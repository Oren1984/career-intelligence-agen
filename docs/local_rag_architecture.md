# Local RAG Architecture

## Overview

The Career Intelligence Agent uses a **fully local, privacy-first RAG (Retrieval-Augmented Generation)** architecture to provide grounded career analysis and Q&A.

All processing happens on your machine. No documents are sent to cloud services. No API keys are required for the core retrieval pipeline.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE ONLY                        │
│                                                              │
│  knowledge_base/                data/knowledge_index/        │
│  ├── resume/         ──────►   ├── index.json               │
│  ├── projects/       ingest    └── metadata.json            │
│  ├── skills/                            │                    │
│  ├── experience/                        │ load               │
│  └── strategy/                         ▼                    │
│                                  LocalIndex                  │
│                                  (TF-IDF vectors)            │
│                                         │                    │
│  Job Description ──► RAGJobAnalyzer ──► KnowledgeRetriever  │
│                                         │                    │
│  Career Question ──► CareerQAService ──►┘                    │
│                            │                                 │
│                            ▼                                 │
│                    RetrievalResult                           │
│                    (chunks + scores)                         │
│                            │                                 │
│                    ManualJobAnalyzer                         │
│                    (CareerScorer + GapAnalyzer +             │
│                     PortfolioMatcher + ActionPlanner)        │
│                            │                                 │
│                    RAGAnalysisResult                         │
│                    (scores + evidence + gaps)                │
│                            │                                 │
│                    Streamlit Dashboard                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Map

| Module | Responsibility |
|--------|----------------|
| `app/rag/document_loader.py` | Load `.md`, `.txt`, `.pdf`, `.json` files from `knowledge_base/` |
| `app/rag/chunker.py` | Split documents into retrievable chunks (~800 chars) with overlap |
| `app/rag/indexer.py` | Build local TF-IDF index; save/load to `data/knowledge_index/index.json` |
| `app/rag/retriever.py` | Top-k TF-IDF cosine similarity retrieval; job-specific multi-query |
| `app/rag/knowledge_service.py` | Orchestrates ingest → index → retrieve; module-level singleton |
| `app/rag/qa_service.py` | Evidence-grounded career Q&A; synthesizes answers from retrieved chunks |
| `app/services/rag_job_analysis.py` | Extends manual job analysis with RAG evidence |
| `dashboard/streamlit_app.py` | Adds Knowledge Base tab + Career Q&A tab; extends job analysis display |
| `scripts/ingest_knowledge.py` | CLI ingestion command |
| `scripts/rebuild_index.py` | CLI force-rebuild command |

---

## Ingestion Flow

```
1. document_loader.load_documents(kb_root)
   → Scans knowledge_base/ recursively
   → Loads .md, .txt, .pdf, .json files
   → Infers category from folder name (resume, projects, skills, etc.)
   → Returns list[RawDocument]

2. chunker.chunk_documents(documents)
   → Splits each document by paragraphs (blank-line separated)
   → If paragraph > max_chars (800): split further by sentences
   → Applies overlap (~80 chars) between adjacent chunks
   → Filters chunks < min_chars (40)
   → Returns list[DocumentChunk] with metadata

3. indexer.build_index(chunks)
   → Tokenizes each chunk (lowercase, remove stop words)
   → Computes TF-IDF vectors (pure Python, no external deps)
   → Builds inverted index: term → [chunk_indices]
   → Returns LocalIndex

4. indexer.save_index(index, data/knowledge_index/)
   → Serializes index to index.json
   → Saves metadata.json with stats
```

---

## Retrieval Flow

```
1. Query arrives (from job description or career question)

2. KnowledgeRetriever.retrieve(query, top_k)
   → Tokenizes query
   → Computes TF-IDF query vector
   → Cosine similarity vs all chunk vectors
   → Deduplicates adjacent chunks from same document
   → Returns top-k RetrievedChunk sorted by score desc

3. For job analysis (retrieve_for_job):
   → Multi-query: full JD text + top-frequency terms
   → Merges results, deduplicates, sorts by score
```

---

## RAG Analysis Flow (Job Description)

```
1. User pastes job description in dashboard

2. RAGJobAnalyzer.analyze(job_text)
   → parse_job_text() extracts title, skills, seniority
   → ManualJobAnalyzer.analyze() runs full scoring:
       - CareerScorer: 7-dimensional fit (0-100)
       - GapAnalyzer: easy/medium/hard gaps
       - ActionPlanner: prioritized next steps
       - PortfolioMatcher: best project to highlight
       - CareerDirectionAnalyzer: career track fit
   → KnowledgeRetriever.retrieve_for_job() gets evidence
   → Evidence classified: project / skill / experience
   → Missing evidence identified for each gap
   → Returns RAGAnalysisResult

3. Dashboard displays:
   → Fit score + breakdown
   → Apply decision
   → Strengths, gaps, risks
   → Action plan
   → Portfolio recommendation
   → Retrieved evidence (expandable)
   → Missing evidence notes
   → Evidence coverage indicator
```

---

## Q&A Flow

```
1. User types career question in Career Q&A tab

2. CareerQAService.ask(question)
   → KnowledgeService.retrieve(question, top_k=5)
   → _assess_confidence(retrieved): high / medium / low / none
   → _synthesize_answer_from_evidence(): extract relevant sentences
   → Returns QAAnswer with answer + evidence + confidence + sources

3. Dashboard displays:
   → Answer text
   → Confidence indicator
   → Evidence chunks (expandable)
   → Source file references
```

---

## Privacy Model

- **All documents stay local.** `knowledge_base/` is processed only on your machine.
- **No cloud calls.** TF-IDF retrieval uses only Python stdlib — no API keys.
- **Git protection.** `knowledge_base/resume/`, `knowledge_base/projects/`, etc. are all gitignored.
- **Only safe samples committed.** `knowledge_base/_samples/` contains placeholder files only.
- **Index stays local.** `data/knowledge_index/` is gitignored and never committed.
- **Optional LLM** (Claude/OpenAI/Gemini) is for job scraping pipeline only, not for RAG retrieval.

---

## TF-IDF Retrieval Design

The retrieval engine is a pure Python TF-IDF implementation:

- **No external dependencies** for core retrieval (no sklearn, no sentence-transformers required)
- **Tokenization:** lowercase, punctuation removal, stop word filtering
- **TF:** term frequency within document
- **IDF:** `log((1 + n_docs) / (1 + df)) + 1` (sklearn-style smooth IDF)
- **Similarity:** sparse cosine similarity between query and chunk vectors
- **Storage:** JSON (human-readable, no binary pickles)

This is simpler and more transparent than embedding-based retrieval, with no dependencies.
For higher-quality semantic retrieval, `sentence-transformers` can be layered in later.

---

## Local-Only Design Decisions

1. **Pure Python TF-IDF** instead of vector embeddings — works offline, zero extra deps
2. **JSON index storage** instead of binary pickle — readable, debuggable, portable
3. **No cloud vector DB** (no Pinecone, Weaviate, Qdrant) — everything in `data/knowledge_index/`
4. **Optional LLM for synthesis** — Q&A works without any LLM (rule-based synthesis)
5. **Gitignore for personal content** — privacy-safe by default
