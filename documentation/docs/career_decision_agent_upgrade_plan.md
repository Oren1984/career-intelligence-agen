# Career Decision Agent — Upgrade Plan

**Branch:** feature/career-decision-agent-v2
**Date:** 2026-03-24

---

## 1. Original System

The V1 system was a job collection and scoring tool:

- Collected jobs from RSS feeds, ATS integrations (Greenhouse/Lever), and Israeli job boards
- Stored jobs in SQLite via SQLAlchemy ORM
- Scored jobs using a 3-tier engine: V1 (keyword), V2 (semantic themes), V3 (embeddings)
- Displayed results in a Streamlit dashboard with high/medium/low classification
- Supported basic status management (new, reviewing, saved, ignored, applied_manual)

**What it lacked:** The system was a search engine, not a decision engine. It could find and rank jobs, but could not explain *why* to apply, *what was missing*, or *where to focus next*.

---

## 2. Target Upgraded Vision

Transform the system into a **Career Decision Agent** that:

- **Understands the user** at a career strategy level (goals, track, experience, work mode)
- **Scores jobs across 7 dimensions** with a weighted overall fit score (0–100)
- **Explains every score** — strengths, gaps, risks, per dimension
- **Identifies gaps** — easy vs hard, with close strategies
- **Generates action plans** — per-job next steps (CV, portfolio, skills, interview)
- **Matches portfolio projects** — recommends which project to lead with
- **Classifies career direction** — aligned, partial, off-track, transition
- **Assigns recommendation labels** — Apply Now, Stretch, Not Worth It, etc.
- **Supports feedback** — lightweight signal recording
- **Produces weekly reviews** — strategic summaries and focus recommendations

---

## 3. Three Implementation Phases

### Phase 1 — Personalized Matching Engine

**Goal:** Turn keyword scoring into explainable, multi-factor career decision scoring.

Key changes:
1. **Extended `CandidateProfile`** — added `experience_level`, `work_mode_preference`, `preferred_role_track`, `short_term_goal`, `long_term_goal`, `preferred_domains`, `willingness_to_learn`, `career_tracks`, and more
2. **Updated `config/profile.yaml`** — new sections for all extended fields
3. **Created `app/matching/career_scorer.py`** — the core of the upgrade:
   - 7-dimension scoring: title_relevance, skill_overlap, seniority_realism, domain_alignment, work_mode_alignment, strategic_alignment, portfolio_alignment
   - Weighted overall fit score (0–100)
   - Recommendation labels (7 categories)
   - Explainable output: strengths, gaps, risks, action items
4. **New DB model `CareerScore`** — stores all career decision data per job
5. **`JobService` extended** — `career_score_all_unscored()`, `get_jobs_with_career_scores()`, `get_career_summary_stats()`

### Phase 2 — Decision Agent Capabilities

**Goal:** Add gap analysis, action plans, portfolio matching, and career direction classification.

Key changes:
1. **`app/matching/gap_analyzer.py`** — classifies missing skills into easy/medium/hard, provides close strategies
2. **`app/matching/action_planner.py`** — generates prioritized per-job action plans (CV, portfolio, skills, interview)
3. **`app/matching/portfolio_matcher.py`** — ranks portfolio projects against job requirements, recommends which to lead with
4. **`app/matching/career_direction.py`** — classifies jobs into career tracks and evaluates direction alignment

### Phase 3 — Active Agent Features

**Goal:** Make the system continuously useful with feedback, weekly reviews, and an upgraded UI.

Key changes:
1. **`app/matching/weekly_review.py`** — generates strategic weekly summaries from accumulated career score data
2. **New DB model `JobFeedback`** — stores lightweight signals (liked, applied, wrong_direction, etc.)
3. **`JobService` extended** — `record_feedback()`, `get_feedback_summary()`, `generate_weekly_review()`
4. **Upgraded `dashboard/streamlit_app.py`** — Decision Console tab, Weekly Review tab, career score breakdown cards, feedback buttons

---

## 4. Architecture Decisions

### Why a separate `CareerScore` table?

Preserving backward compatibility was critical. Adding a new table means:
- Existing `Score` data (V1/V2) is untouched
- V1 and V2 scoring pipelines continue working
- The new career scoring is opt-in — old functionality still runs if CareerScore hasn't been populated

### Why deterministic (rule-based) scoring vs. LLM scoring?

The requirement was for *explainable* and *demo-friendly* scoring. A deterministic multi-factor model:
- Is always available (no API key needed)
- Runs in milliseconds per job
- Produces consistent, reproducible results
- Can be tested with unit tests
- Is transparent — every score can be explained by the formula

LLM analysis remains available as an optional enhancement via the existing `get_provider()` system.

### Why word-boundary matching in `_extract_skill_tokens`?

Initial substring matching caused false positives (e.g., "r" matching inside "marketing"). Word-boundary matching via `re.search(r"\b...\b", text)` ensures skill tokens are matched as whole words, improving precision.

### Why 7 scoring dimensions?

Each dimension captures a different aspect of job-candidate fit:
- `title_relevance` — is this even the right kind of role?
- `skill_overlap` — does the candidate have the required skills?
- `seniority_realism` — is the level realistic?
- `domain_alignment` — is the domain what the candidate wants?
- `work_mode_alignment` — can they actually work this way?
- `strategic_alignment` — does it fit career goals?
- `portfolio_alignment` — can the candidate demonstrate fit?

Weights sum to 1.0: skill_overlap (25%) and title_relevance (20%) are most important; portfolio_alignment (5%) is supplementary.

---

## 5. Preserved Components

All V1 components are fully preserved:
- `app/collectors/` — all collectors unchanged
- `app/dedup/` — dedup engine unchanged
- `app/matching/scorer.py`, `semantic_scorer.py`, `embedding_scorer.py`, `combined_scorer.py` — all preserved
- `app/filtering/filter_engine.py` — unchanged
- `app/db/normalizer.py` — unchanged
- `app/llm/` — all LLM providers unchanged
- `app/notifications/` — notification system unchanged
- `app/scheduler/` — scheduler unchanged
- All 379 original tests continue to pass
