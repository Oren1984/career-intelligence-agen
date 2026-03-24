# Validation Report — Local RAG Career Intelligence

**Date:** 2026-03-24
**Branch:** feature/local-rag-career-intelligence
**Test runner:** pytest

---

## Test Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_rag_document_loader.py` | 17 | ✅ All passed |
| `test_rag_chunker.py` | 17 | ✅ All passed |
| `test_rag_indexer.py` | 20 | ✅ All passed |
| `test_rag_retriever.py` | 17 | ✅ All passed |
| `test_rag_knowledge_service.py` | 18 | ✅ All passed |
| `test_rag_qa_service.py` | 15 | ✅ All passed |
| `test_rag_job_analysis.py` | 23 | ✅ All passed |
| **RAG Total** | **127** | ✅ **127/127 passed** |
| **Pre-existing tests** | 505 | ✅ All passed |
| **Grand Total** | **632** | ✅ **632/632 passed** |

**Zero regressions.** All pre-existing tests continue to pass.

---

## Scenarios Validated

### FLOW A — Document Ingestion

| Scenario | Result | Notes |
|----------|--------|-------|
| Load .md files from category folders | ✅ PASS | Category inferred from folder name |
| Load .txt files | ✅ PASS | UTF-8 with error replacement |
| Load .json files (dict and list) | ✅ PASS | Converted to readable text |
| Skip hidden files (`.hidden.md`) | ✅ PASS | Files starting with `.` are skipped |
| Skip unsupported extensions (.html) | ✅ PASS | Only .md/.txt/.pdf/.json supported |
| Empty knowledge base directory | ✅ PASS | Returns empty list gracefully |
| Non-existent directory | ✅ PASS | Returns empty list with warning |
| Category inference from subfolder | ✅ PASS | resume/ → "resume", projects/ → "projects" |

### FLOW A — Chunking

| Scenario | Result | Notes |
|----------|--------|-------|
| Short text stays as single chunk | ✅ PASS | Under max_chars → one chunk |
| Long paragraph split by sentence | ✅ PASS | Respects max_chars boundary |
| Multiple paragraphs split correctly | ✅ PASS | Blank line = paragraph separator |
| Overlap applied between chunks | ✅ PASS | Tail of previous chunk prepended |
| Short chunks filtered (< min_chars) | ✅ PASS | min_chars=40 by default |
| Empty document produces no chunks | ✅ PASS | |
| Chunk IDs are unique | ✅ PASS | Format: `doc_id::chunk{index}` |
| Metadata preserved in chunks | ✅ PASS | category, file_name, doc_id |

### FLOW A — Indexing

| Scenario | Result | Notes |
|----------|--------|-------|
| Build TF-IDF index from chunks | ✅ PASS | Pure Python, no external deps |
| Empty chunk list → empty index | ✅ PASS | Graceful handling |
| Query finds most relevant chunk | ✅ PASS | RAG query → RAG chunk ranks first |
| Results sorted by descending score | ✅ PASS | |
| Empty query returns no results | ✅ PASS | |
| top_k respected | ✅ PASS | |
| Save index to JSON | ✅ PASS | Human-readable JSON format |
| Load index from JSON | ✅ PASS | All chunks and vectors restored |
| Round-trip query consistency | ✅ PASS | Same results before/after save+load |

### FLOW A — Retrieval

| Scenario | Result | Notes |
|----------|--------|-------|
| Retrieval returns relevant chunks | ✅ PASS | Cosine similarity ranking |
| Category filter works | ✅ PASS | Only returns chunks from specified categories |
| No match returns empty result | ✅ PASS | Unknown terms → empty |
| Empty index returns empty result | ✅ PASS | |
| Job-specific multi-query retrieval | ✅ PASS | Broader coverage for job descriptions |
| No duplicate chunks in results | ✅ PASS | Deduplication by chunk_id |
| Evidence formatted for display | ✅ PASS | `as_context_string()` renders cleanly |

### FLOW B — RAG Job Analysis

| Scenario | Result | Notes |
|----------|--------|-------|
| Full RAG analysis pipeline | ✅ PASS | Scores + evidence combined |
| Evidence retrieved for matching job | ✅ PASS | AI Engineer JD → AI project evidence |
| No evidence when KB not indexed | ✅ PASS | Graceful degradation |
| Evidence coverage assessed correctly | ✅ PASS | high/medium/low/none |
| Missing evidence identified | ✅ PASS | Gaps without KB support flagged |
| Title/company/location overrides work | ✅ PASS | |
| Empty job description raises error | ✅ PASS | ValueError from parser |
| to_dict() includes RAG section | ✅ PASS | Nested `rag` key in output dict |
| apply_only mode includes evidence | ✅ PASS | coverage + evidence_used in output |
| portfolio_only mode with evidence | ✅ PASS | project_evidence included |
| Weak match scenario | ✅ PASS | Unrelated job still analyzed without crash |

### FLOW C — Career Q&A

| Scenario | Result | Notes |
|----------|--------|-------|
| Question with evidence answered | ✅ PASS | Evidence-grounded synthesis |
| Question with no KB returns clear message | ✅ PASS | "run ingest" instruction shown |
| Empty question handled | ✅ PASS | Graceful message |
| Sources populated from evidence | ✅ PASS | List of file names returned |
| Confidence rating assigned | ✅ PASS | high/medium/low/none |
| Batch Q&A | ✅ PASS | ask_batch() returns list[QAAnswer] |
| Skill summary | ✅ PASS | `summarize_skills("Docker")` works |
| Project-for-role recommendation | ✅ PASS | `find_best_project_for_role("MLOps")` works |

---

## Manual Verification Checks

| Check | Status | Notes |
|-------|--------|-------|
| `python scripts/ingest_knowledge.py` runs cleanly | ✅ | Verified on sample KB |
| `python scripts/rebuild_index.py` runs cleanly | ✅ | Verified |
| `data/knowledge_index/index.json` created after ingest | ✅ | JSON format, readable |
| `.gitignore` blocks personal content | ✅ | `knowledge_base/resume/` etc. gitignored |
| New dashboard tabs render without error | ✅ | Knowledge Base and Career Q&A tabs load |
| Existing dashboard tabs unaffected | ✅ | No regressions in existing tabs |
| RAGJobAnalyzer falls back gracefully | ✅ | No KB → uses ManualJobAnalyzer output only |

---

## Known Limitations

1. **TF-IDF vs semantic retrieval:** Keyword-based TF-IDF may miss conceptual synonyms.
   Example: "vector store" and "ChromaDB" as separate queries may retrieve differently.
   Mitigation: Optional `sentence-transformers` support can be layered in later.

2. **PDF quality:** Image-based PDFs cannot be text-extracted. Text-based PDFs work via `pypdf`.

3. **Q&A synthesis is rule-based:** Answers are constructed from retrieved text snippets,
   not synthesized by an LLM. Answers may feel fragmented for complex questions.
   Mitigation: Optional LLM synthesis can be added; the interface is already designed for it.

4. **Index staleness:** If documents change, user must manually re-run ingest.
   Mitigation: Clear documentation + dashboard rebuild button.

5. **Short documents may produce poor chunks:** Very short files (< 80 chars) may be
   chunked suboptimally. Mitigation: min_chars filter removes trivially short chunks.

---

## What Was NOT Tested (Future Work)

- PDF ingestion with real PDF files (requires pypdf installed, not mocked in tests)
- End-to-end Streamlit UI tests (no Selenium/Playwright test layer)
- Performance testing with large KB (1000+ documents)
- Optional `sentence-transformers` semantic retrieval path
