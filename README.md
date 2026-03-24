# Career Intelligence Agent — Local RAG Edition

A **local, privacy-first Career Intelligence Agent** with RAG-powered job analysis and career knowledge retrieval.

All your career documents stay on your machine. No cloud required. No API keys needed for core features.

---

## What Local RAG Means Here

**RAG (Retrieval-Augmented Generation)** means the system grounds its analysis in your actual career documents:

1. You place private career files (resume, project notes, skills inventory) in `knowledge_base/`
2. The system indexes them locally using TF-IDF (no embeddings API needed)
3. When you analyze a job, the system **retrieves relevant evidence from your documents**
4. Recommendations are backed by retrieved evidence — not generic guesses
5. You can ask questions like *"Which of my projects best supports an MLOps role?"*

**Everything stays local.** Documents never leave your machine.

---

## What This System Does

**Decision-support, not automation.** This agent helps you make better career decisions:

- **Ingests local career knowledge** — resume, projects, skills, experience, strategy notes
- **Retrieves relevant evidence** — TF-IDF local retrieval against your documents
- **Analyzes pasted job descriptions** — with grounded evidence from your own materials
- **Scores jobs intelligently** — 7-dimensional fit scoring (0–100) with full breakdown
- **Explains every recommendation** — strengths, gaps, risks, retrieved evidence, source refs
- **Labels each opportunity** — Apply Now, Apply After Small Fix, Stretch, Not Worth It, etc.
- **Identifies skill gaps** — easy vs hard to close, with evidence check
- **Matches portfolio projects** — recommends which project to lead with per role
- **Answers career questions** — *"What Docker experience do I have?"* — with evidence
- **Weekly strategic review** — recurring gaps, top opportunities, focus recommendations

> The system **never auto-applies** or sends CVs. You stay in full control.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python scripts/init_db.py

# 3. Add your career documents (optional but recommended)
# Place .md or .txt files in:
#   knowledge_base/resume/
#   knowledge_base/projects/
#   knowledge_base/skills/
#   (see knowledge_base/README.md for guidance)

# 4. Ingest knowledge base
python scripts/ingest_knowledge.py

# 5. Fetch demo jobs
python scripts/fetch_jobs.py --mode mock

# 6. Launch dashboard
streamlit run dashboard/streamlit_app.py
```

Open `http://localhost:8501`.

**Without your own documents:** Use the sample files in `knowledge_base/_samples/` — they work as demo content.

---

## Ingest Your Career Knowledge

```bash
# First-time ingest
python scripts/ingest_knowledge.py

# After adding or editing documents
python scripts/rebuild_index.py
```

Your personal files are **gitignored by default** — they will never be committed to version control.

---

## Manual Job Analysis (Paste Mode)

Analyze any external job posting without using the job collectors.

**How to use:**
1. Open the dashboard → **"Analyze External Job"** tab
2. Optionally fill in Job Title, Company, Location
3. Paste the full job description into the text area
4. Choose an action:
   - **Analyze This Job** — full pipeline: fit score, recommendation, gaps, action plan, portfolio match, career direction
   - **Should I Apply?** — focused output: YES / NO / CONDITIONAL + top 2 actions
   - **Which Project Should I Highlight?** — ranked portfolio matches only

**What you get:**
- Fit score (0–100) with per-dimension breakdown
- Recommendation label (Apply Now, Stretch Opportunity, etc.)
- Strengths, gaps, and risks extracted from the posting
- Prioritised action plan (CV, portfolio, skills, interview)
- Best portfolio project to lead with, and why
- Career track classification and direction alignment

**Example usage:**
```python
from app.services.manual_job_analysis import ManualJobAnalyzer
from app.candidate.profile_loader import load_candidate_profile

profile = load_candidate_profile()
analyzer = ManualJobAnalyzer(profile=profile.to_dict())

result = analyzer.analyze(
    raw_text="We are looking for an AI Engineer with Python, LangChain, RAG...",
    title="AI Engineer",
    company="Acme AI",
)

print(result.overall_fit_score)        # e.g. 84.0
print(result.recommendation_label)    # e.g. "Apply Now"
print(result.apply_decision)          # YES / NO / CONDITIONAL
print(result.action_items)            # prioritised next steps
print(result.best_matching_project)   # which portfolio project to lead with
```

---

## Career Decision Scoring (V2)

The core scoring engine evaluates each job across 7 weighted dimensions:

| Dimension | Weight |
|---|---|
| Skill Overlap | 25% |
| Title Relevance | 20% |
| Seniority Realism | 15% |
| Domain Alignment | 15% |
| Work Mode Alignment | 10% |
| Strategic Alignment | 10% |
| Portfolio Alignment | 5% |

**Overall fit = weighted average × 10 → 0–100 score**

### Recommendation Labels

| Label | Meaning |
|---|---|
| Apply Now | Strong fit, no major blockers |
| Apply After Small Fix | Good fit, 1–2 fixable gaps |
| Stretch Opportunity | Worth effort with targeted preparation |
| Good Role, Wrong Timing | Right kind of role, seniority is the gap |
| Good Company, Wrong Role | Work mode or focus mismatch |
| Market Signal Only | Useful for learning what the market wants |
| Not Worth It | Too many mismatches |

---

## Data Flow

```
config/profile.yaml + data/candidate_profile/
       ↓
CandidateProfile (V2 extended)
       ↓
Job Sources → Collection → Dedup → SQLite
       ↓
CareerScorer (V2) + CombinedScorer (V1/V2/V3)
       ↓
Decision Console Dashboard
```

---

## Dashboard Tabs

- **Decision Console** — career-scored jobs with fit scores, labels, breakdown, gaps, action items
- **Classic Jobs** — V1 keyword/semantic scored view
- **Analytics** — label distribution, source breakdown, feedback signals
- **Weekly Review** — strategic summary, recurring gaps, direction insights, focus recommendations
- **Candidate Profile** — full V2 profile view with career tracks and goals

---

## Source Modes

Set `SOURCE_MODE` environment variable:

| Mode | Description |
|---|---|
| `mock` | Hardcoded demo jobs (no network required) |
| `rss` | Remote job feeds (We Work Remotely, etc.) |
| `israel` | Israeli job boards (Drushim, AllJobs) |
| `all` | All enabled sources |

---

## Candidate Profile

Edit `config/profile.yaml` to configure your career strategy:

```yaml
target_roles:
  - Applied AI Engineer
  - LLM Engineer

experience_level: mid           # junior | mid | senior
work_mode_preference: remote    # remote | hybrid | onsite | any

preferred_domains:
  - AI/ML Engineering
  - LLM Applications

short_term_goal: >
  Build LLM-powered applications and MLOps pipelines.

career_tracks:
  primary: Applied AI / LLM Engineer
  acceptable:
    - MLOps Engineer
  avoid:
    - Data Analyst
```

Add your portfolio projects in `data/candidate_profile/projects.json`.

---

## Tech Stack

- **Backend:** Python, SQLAlchemy, SQLite
- **Frontend:** Streamlit
- **Scoring:** Multi-factor career decision engine (deterministic, explainable)
- **Classic Scoring:** keyword + sentence-transformers (optional)
- **Job Sources:** RSS feeds, Greenhouse/Lever ATS, Israeli boards, mock data
- **LLM (optional):** Anthropic Claude, OpenAI, Google Gemini, Ollama (mock fallback)
- **Deployment:** Docker + docker-compose

---

## Tests

```bash
python -m pytest tests/ -q
# 455 passed
```

---

## Documentation

- `documentation/docs/current_state_audit.md` — V1 state audit
- `documentation/docs/career_decision_agent_upgrade_plan.md` — Architecture and upgrade plan
- `documentation/docs/validation_report.md` — Test results and validation scenarios
- `documentation/docs/final_upgrade_summary.md` — Full upgrade summary and run checklist

---

## Design Principle

**Decision-support, not automation.**
This system helps you make better career choices — it does not apply to jobs, send CVs,
or take automated actions on your behalf.
