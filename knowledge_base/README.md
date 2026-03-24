# Local Knowledge Base

This folder contains your private career knowledge files for local RAG analysis.

**Privacy note:** This folder is gitignored (except for sample files in `_samples/`).
Your personal documents will NOT be committed to git.

## Folder Structure

```
knowledge_base/
├── resume/          — Your CV, resume, or career summary
├── projects/        — Project writeups, READMEs, summaries
├── skills/          — Skills inventory, tech stack notes
├── experience/      — Work experience notes, role summaries
├── achievements/    — Awards, certifications, accomplishments
├── strategy/        — Career goals, job search strategy
├── interview_prep/  — Interview notes, talking points
└── _samples/        — Safe placeholder examples (committed to git)
```

## Supported File Formats

- `.md` — Markdown (recommended)
- `.txt` — Plain text
- `.pdf` — PDF documents (requires pypdf)
- `.json` — Structured data (auto-converted to text)

## How to Use

1. Add your personal documents to the relevant category folders
2. Run ingestion: `python scripts/ingest_knowledge.py`
3. Open the dashboard: `streamlit run dashboard/streamlit_app.py`
4. Use "Knowledge Base" tab to verify ingestion
5. Use "Analyze External Job" tab for RAG-augmented job analysis
6. Use "Career Q&A" tab to ask questions about your materials

## Rebuilding After Changes

After adding, editing, or deleting documents:

```bash
python scripts/rebuild_index.py
```

## What Makes Good Knowledge Base Content?

- **Resume/CV** — detailed project descriptions, technology stack, responsibilities
- **Project notes** — what you built, why, what challenges you solved, what tech you used
- **Skills inventory** — explicit list of skills with proficiency levels
- **Experience notes** — role descriptions, key achievements, technologies used
- **Career strategy** — target roles, companies, criteria for applying
- **Interview prep** — common questions, talking points, stories to tell

The more specific and detailed your documents, the better the RAG retrieval quality.
