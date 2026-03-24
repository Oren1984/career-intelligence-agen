# Local RAG Usage Guide

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your career documents to knowledge_base/
cp your_resume.md knowledge_base/resume/
cp your_project_notes.md knowledge_base/projects/
# (see folder structure below)

# 3. Ingest your documents
python scripts/ingest_knowledge.py

# 4. Launch the dashboard
streamlit run dashboard/streamlit_app.py
```

---

## Step 1: Add Your Documents

Place your personal career files in the relevant category folder:

```
knowledge_base/
├── resume/          ← Your CV, resume, or career summary (.md or .pdf)
├── projects/        ← Project writeups, READMEs, technical summaries
├── skills/          ← Skills inventory, tech stack notes, proficiency levels
├── experience/      ← Work history, role descriptions, key achievements
├── achievements/    ← Awards, certifications, accomplishments
├── strategy/        ← Career goals, target roles, job search strategy
├── interview_prep/  ← Common questions, talking points, STAR stories
└── _samples/        ← Safe example files (committed to git, for demo)
```

### Recommended file formats
- `.md` — Markdown (best for rich structure)
- `.txt` — Plain text (simplest)
- `.pdf` — PDF documents (requires pypdf, already in requirements)

### What makes good knowledge base content?

The retrieval quality depends on your document richness. Include:

- **Resume/CV:** Full project descriptions with technology names, quantified achievements, role descriptions
- **Projects:** What you built, why, what technologies you used, what challenges you solved, what impact it had
- **Skills:** Explicit skill names with context ("proficient in Docker, Kubernetes, Terraform")
- **Experience:** Role titles, company types, key responsibilities, technologies used
- **Strategy:** Target roles, deal breakers, what you're looking for

The more specific and detailed your documents, the better the retrieval quality.

---

## Step 2: Ingest Documents

```bash
# Standard ingest (skips if already indexed)
python scripts/ingest_knowledge.py

# Force rebuild after adding/changing documents
python scripts/rebuild_index.py

# Ingest from a custom location
python scripts/ingest_knowledge.py --kb-root /path/to/my/docs

# Verbose mode for debugging
python scripts/ingest_knowledge.py --verbose
```

**Output example:**
```
============================================================
INGESTION COMPLETE
============================================================
  Documents:   8
  Chunks:      47
  Categories:  experience, projects, resume, skills, strategy
  Indexed at:  2026-03-24T12:00:00
  Index dir:   data/knowledge_index
============================================================
```

---

## Step 3: Analyze a Job Description

1. Open the dashboard: `streamlit run dashboard/streamlit_app.py`
2. Click the **"Analyze External Job"** tab
3. Paste a job description
4. Click **"Analyze This Job"**

The analysis will now include:
- **Evidence Coverage** indicator (🟢 Strong / 🟡 Moderate / 🟠 Weak / ⚪ None)
- **Retrieved Evidence** (expandable — shows which of your documents matched)
- **Missing Evidence Notes** (which gaps have no supporting evidence)
- All existing scores: fit score, breakdown, strengths, gaps, apply decision, portfolio recommendation

---

## Step 4: Ask Career Questions (Q&A)

1. Open the dashboard
2. Click the **"Career Q&A"** tab
3. Type a question or select an example
4. Click **"Ask"**

Example questions:
- *"Which of my projects best demonstrates RAG or LLM work?"*
- *"What evidence do I have for Docker and Kubernetes experience?"*
- *"What recurring skill gaps appear in my materials?"*
- *"Which project should I highlight for an MLOps Engineer role?"*
- *"What AWS and cloud infrastructure experience do I have?"*

Each answer shows:
- The synthesized answer grounded in your documents
- Confidence level
- Expandable evidence chunks (source + relevance score)
- Source file references

---

## Step 5: Manage the Knowledge Base

Use the **"Knowledge Base"** tab in the dashboard to:
- See ingestion status (document count, chunk count, categories)
- View when the index was last built
- Re-ingest or rebuild directly from the UI

---

## Rebuild After Changes

**Always rebuild the index after editing your documents:**

```bash
python scripts/rebuild_index.py
```

Or click **"Rebuild Index"** in the Knowledge Base tab.

---

## Privacy: Keeping Your Documents Out of Git

Personal files in `knowledge_base/` are gitignored by default:

```
knowledge_base/resume/        ← gitignored
knowledge_base/projects/      ← gitignored
knowledge_base/skills/        ← gitignored
knowledge_base/experience/    ← gitignored
knowledge_base/achievements/  ← gitignored
knowledge_base/strategy/      ← gitignored
knowledge_base/interview_prep/ ← gitignored
data/knowledge_index/         ← gitignored (generated index)
```

**Only these are committed to git:**
- `knowledge_base/README.md`
- `knowledge_base/_samples/` (safe placeholder examples)

**To verify nothing personal is staged:**
```bash
git status
git diff --staged
```

---

## Troubleshooting

**No evidence retrieved:**
- Make sure you ran `python scripts/ingest_knowledge.py` first
- Check the Knowledge Base tab to verify indexing succeeded
- Add more specific documents to `knowledge_base/` (the more detail, the better)

**Dashboard shows "Knowledge base not indexed":**
- Run `python scripts/ingest_knowledge.py`
- Or click "Ingest Knowledge Base" in the Knowledge Base tab

**PDF not loading:**
- Ensure `pypdf` is installed: `pip install pypdf`
- Some PDFs are image-based and cannot be text-extracted

**Index out of date:**
- Run `python scripts/rebuild_index.py` after any document changes

**Low confidence answers:**
- Add more specific documents to the relevant category
- Use more detailed project descriptions and skill notes
- Make sure you've included the exact technologies/skills in your documents
