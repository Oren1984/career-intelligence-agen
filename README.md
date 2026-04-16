# Career Intelligence Agent — Local RAG Edition

A **privacy-first Career Intelligence Agent** that helps you make better career decisions using your own data.

✔ Fully local — no cloud required  
✔ No API keys needed for core features  
✔ Evidence-based recommendations (RAG)  
✔ Built for real decision-making — not demos  

---

## 🎯 What This System Does

This is a **decision-support system**, not an automation tool.

It helps you:

- Analyze job descriptions intelligently
- Match jobs against your real experience
- Identify skill gaps and priorities
- Recommend which projects to showcase
- Provide structured career insights

> You stay in control — the system never applies to jobs automatically.

---

## 🧠 How Local RAG Works

1. You place your career documents in `knowledge_base/`
2. The system indexes them locally (TF-IDF)
3. When analyzing jobs → it retrieves relevant evidence
4. All outputs are grounded in your own data

**Nothing leaves your machine.**

---

## ⚡ Quick Start (Local Run)

```bash
pip install -r requirements.txt
python scripts/init_db.py
python scripts/ingest_knowledge.py
python scripts/fetch_jobs.py --mode mock
streamlit run dashboard/streamlit_app.py
```

Open: http://localhost:8508

---

## 🐳 Run with Docker (Recommended)

```bash
docker compose up --build
```

Open: http://localhost:8508

Stop

```bash
docker compose down
```

---

## 📂 Project Structure
config/
data/
knowledge_base/
scripts/
app/
dashboard/
tests/
documentation/

---

## 📊 Core Capabilities
- Job Analysis
  - Fit score (0–100)
  - Recommendation label (Apply / Stretch / Skip)
  - Strengths and gaps detection
  - Risk analysis

---

## 📊 Core Capabilities
- Job Analysis
  - Fit score (0–100)
  - Recommendation label (Apply / Stretch / Skip)
  - Strengths and gaps detection
  - Risk analysis

---

## 📊 Portfolio Matching
  - Recommends best project per job
  - Explains why it fits
  - Aligns with role expectations
  
---

## 📊 Career Insights
  - Weekly strategic review
  - Recurring skill gaps
  - Direction alignment

---

## 📊 Q&A Over Your Career

Ask:

- "What Docker experience do I have?"
- "Which project supports MLOps roles?"

Answers are evidence-based from your documents

---

## 🧮 Scoring System (V2)

Dimension	          Weight
Skill Overlap	        25%
Title Relevance	      20%
Seniority	            15%
Domain Fit	          15%
Work Mode	            10%
Strategy Fit	        10%
Portfolio Match	       5%

---

## 🖥 Dashboard Overview

- Decision Console — main job evaluation
- Classic Jobs — keyword-based scoring
- Analytics — trends & insights
- Weekly Review — strategy guidance
- Profile View — full candidate profile

---

## 🧪 Tests

```bash
python -m pytest tests/ -q
```

---

## ⚙️ Configuration

Edit:
config/profile.yaml

To define:
- Target roles
- Experience level
- Work preferences
- Career direction

---

## 🔌 Source Modes

Set SOURCE_MODE:

Mode	      Description
mock	      Demo data
rss	        Remote jobs
israel	    Local job boards
all	        Everything

---

## 🧱 Tech Stack

- Python
- Streamlit
- SQLite
- SQLAlchemy
- TF-IDF (local retrieval)
- Docker

## 📚 Documentation

- documentation/docs/current_state_audit.md
- documentation/docs/validation_report.md
- documentation/docs/final_upgrade_summary.md

---

## 🎯 Design Principle

Decision-support, not automation

This system helps you think better —
not act automatically.

---

## 👨‍💻 Author

Oren Salmi
🧠 AI Systems Engineer

Intelligent Systems • AI Agents • Data & Automation

---