# Current State Audit — Local RAG Career Intelligence Upgrade

**Date:** 2026-03-24
**Branch:** feature/local-rag-career-intelligence
**Auditor:** Claude Code

---

## 1. What Currently Exists

### Core Architecture
- **Streamlit dashboard** (`dashboard/streamlit_app.py`) with 6 tabs: Decision Console, Classic Jobs, Analytics, Weekly Review, Candidate Profile, Analyze External Job
- **Dual scoring system:** V1 (keyword + semantic) and V2 (7-dimensional career fit, 0-100)
- **Manual job analysis** (`app/services/manual_job_analysis.py`) — paste-and-analyze pipeline, in-memory, no DB writes
- **SQLite persistence** (`data/jobs.db`) via SQLAlchemy ORM
- **Multi-source job collection** (mock, RSS, Israeli boards, ATS APIs, HN)
- **4-layer deduplication** engine
- **LLM provider factory** (Claude, OpenAI, Gemini, Ollama) — optional, lazy-loaded
- **27 test files** (~455 passing tests)
- **Docker + docker-compose** setup

### Candidate Profile Data (already local)
- `data/candidate_profile/summary.txt` — free-text career summary
- `data/candidate_profile/skills.json` — structured skills by category
- `data/candidate_profile/projects.json` — portfolio project list
- `config/profile.yaml` — target roles, preferences, goals, career tracks

### Matching Modules (all reusable)
- `app/matching/career_scorer.py` — 7-factor fit scoring
- `app/matching/gap_analyzer.py` — skill gap classification (easy/medium/hard)
- `app/matching/action_planner.py` — prioritized action items
- `app/matching/portfolio_matcher.py` — project-to-job matching
- `app/matching/career_direction.py` — career track classification
- `app/matching/weekly_review.py` — strategic review

### Optional Embedding Support
- `app/matching/embedding_scorer.py` — sentence-transformers integration (optional, graceful fallback)
- `requirements.txt` does NOT currently include `sentence-transformers` or `scikit-learn`

---

## 2. What Already Supports the Target Architecture

| Component | Status | Notes |
|-----------|--------|-------|
| Candidate profile loading | ✅ Ready | profile_loader.py already reads local files |
| Job scoring pipeline | ✅ Ready | CareerScorer + GapAnalyzer can score any job object |
| Manual job analysis | ✅ Ready | Paste-and-analyze without DB; perfect RAG extension point |
| LLM integration (optional) | ✅ Ready | 4 providers, mock fallback |
| Streamlit dashboard | ✅ Ready | Easy to add new tabs |
| Portfolio matching | ✅ Ready | Can be augmented with retrieved evidence |
| Sentence-transformers hook | ✅ Ready | embedding_scorer.py already has optional ST integration |
| Test infrastructure | ✅ Ready | pytest with conftest.py fixtures |

---

## 3. What Is Missing for True Local RAG

| Missing Component | Priority | Notes |
|-------------------|----------|-------|
| Local knowledge base folder | High | Need `knowledge_base/` with curated docs |
| Document ingestion pipeline | High | Load, parse, chunk .md/.txt/.pdf files |
| Chunker | High | Split docs into retrievable segments with metadata |
| Local index (TF-IDF or semantic) | High | Store and query indexed chunks |
| Retriever | High | Top-k chunk retrieval given a query |
| Knowledge service | High | Orchestrates ingest → index → retrieve |
| RAG job analysis | High | Extend manual_job_analysis to pull evidence |
| Career Q&A service | Medium | Answer questions over local knowledge |
| Dashboard: Knowledge Base tab | Medium | Show ingestion status |
| Dashboard: Q&A tab | Medium | UI for career questions |
| Dashboard: RAG evidence in job analysis | Medium | Show retrieved chunks in paste tab |
| Ingestion scripts | High | `scripts/ingest_knowledge.py`, `rebuild_index.py` |
| Sample knowledge docs | High | Safe placeholder files for demo |
| .gitignore updates | High | Prevent accidental commit of personal docs |

---

## 4. Which Modules Can Be Reused

- **`app/services/manual_job_analysis.py`** — extend by adding a `retrieved_evidence` field to `ManualAnalysisResult` and wiring retriever calls before scoring
- **`app/matching/career_scorer.py`** — no changes needed; receives augmented job text
- **`app/matching/portfolio_matcher.py`** — extend to also check retrieved project evidence
- **`app/matching/gap_analyzer.py`** — reuse as-is
- **`app/matching/action_planner.py`** — reuse as-is
- **`app/candidate/profile_loader.py`** — reuse as-is; local files already loaded
- **`app/matching/embedding_scorer.py`** — reuse semantic similarity logic for retriever
- **`dashboard/streamlit_app.py`** — extend with 2 new tabs; existing tabs extended minimally

---

## 5. Which Modules Need Extension

| Module | What to Add |
|--------|-------------|
| `app/services/manual_job_analysis.py` | `retrieved_evidence` list in result; RAG retriever call |
| `dashboard/streamlit_app.py` | Knowledge Base tab, Q&A tab, evidence display in paste tab |
| `requirements.txt` | Add `scikit-learn` (optional, for TF-IDF) |
| `.gitignore` | Add knowledge_base personal content rules |

---

## 6. Risks and Compatibility Concerns

1. **No scikit-learn in current deps** — TF-IDF retrieval needs either sklearn or a pure-Python fallback. Solution: implement pure Python TF-IDF (no new hard deps) with optional sklearn enhancement.

2. **Existing tests must not break** — The new RAG modules are additive; no existing module is modified structurally.

3. **Dashboard edit risk** — Adding tabs to `streamlit_app.py` requires careful insertion to avoid breaking existing tab references.

4. **PDF parsing** — `pypdf` and `pdfminer.six` are already in requirements; PDF support is available.

5. **Personal data in git** — `knowledge_base/` must be gitignored (personal content) with only sample files committed.

6. **Index staleness** — If knowledge files change, user must re-run ingest. Document clearly.

---

## 7. Final Implementation Plan

### Phase 0 — Audit (this document)
### Phase 1 — Local Knowledge Base + Ingestion
- Create `knowledge_base/` folder with category subfolders
- Create sample/placeholder documents in each category
- Implement `app/rag/document_loader.py` — load .md, .txt, .pdf files
- Implement `app/rag/chunker.py` — split into chunks with metadata
- Implement `app/rag/indexer.py` — build local TF-IDF index (pure Python, no hard deps)
- Implement `app/rag/retriever.py` — top-k BM25/TF-IDF retrieval
- Implement `app/rag/knowledge_service.py` — orchestration layer
- Create `scripts/ingest_knowledge.py` and `scripts/rebuild_index.py`

### Phase 2 — RAG Job Analysis
- Implement `app/rag/qa_service.py` — grounded Q&A
- Implement `app/services/rag_job_analysis.py` — extend manual analysis with retrieval
- Extend `ManualAnalysisResult` to carry `retrieved_evidence`

### Phase 3 — Career Q&A
- `app/rag/qa_service.py` answers freeform career questions with evidence
- Q&A response includes retrieved chunks + source refs

### Phase 4 — Dashboard Integration
- Add Knowledge Base tab to Streamlit
- Add Q&A tab to Streamlit
- Extend Analyze External Job tab with retrieved evidence section
- Show ingestion status (file count, chunk count, last ingest time)

### Phase 5 — Configuration, Safety, Privacy
- Update `.gitignore`
- Create `.env.example` additions
- Create `knowledge_base/README.md`
- Create sample docs (public-safe placeholders)

### Phase 6 — Testing
- Unit tests for each new RAG module
- Integration test for full RAG job analysis flow
- Edge case tests (empty KB, missing files, weak matches)
- Regression: all existing tests must pass

### Phase 7 — Documentation
- `docs/local_rag_architecture.md`
- `docs/local_rag_usage_guide.md`
- `docs/validation_report_local_rag.md`
- `docs/final_local_rag_summary.md`
- Update `README.md`
