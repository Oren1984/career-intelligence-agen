# Current State Audit — NeuroOps Career Agent

**Date:** 2026-03-24
**Auditor:** Claude Code (feature/career-decision-agent-v2)

---

## 1. What the Project Currently Does

The NeuroOps Career Agent is a Python/Streamlit application that:

1. **Collects job listings** from multiple sources (RSS feeds, ATS integrations, mock data, Israeli job boards)
2. **Deduplicates** incoming jobs with a 4-layer engine (URL, source ID, fingerprint, fuzzy)
3. **Stores** jobs in SQLite via SQLAlchemy ORM
4. **Filters** jobs using positive/negative keyword lists from `config/profile.yaml`
5. **Scores** jobs with a 3-tier engine:
   - V1: Keyword-based (adds/subtracts points per keyword)
   - V2: Theme-based semantic matching (6 themes)
   - V3: Sentence-transformer embedding similarity (optional)
   - Combined: V1 score + semantic bonus (max +2.0)
6. **Displays results** in a Streamlit dashboard with tabs (Jobs, Analytics, Profile, Settings)
7. **Notifies** via email/Slack/Telegram when high-match jobs are found
8. **Schedules** periodic collection via APScheduler

---

## 2. What Already Works Well

| Component | Status | Notes |
|---|---|---|
| Job collection pipeline | ✅ Solid | Modular collectors, easy to extend |
| 4-layer deduplication | ✅ Solid | Handles URL, fingerprint, fuzzy |
| SQLite + SQLAlchemy ORM | ✅ Solid | Clean models, session management |
| Multi-tier scoring (V1/V2/V3) | ✅ Solid | Graceful fallback, explanation text |
| Candidate profile loading | ✅ Good | YAML + JSON file structure |
| Streamlit dashboard | ✅ Functional | Tabs, job cards, status management |
| Notification system | ✅ Functional | Multiple channels, sent log tracking |
| APScheduler integration | ✅ Functional | Background scheduling |
| Test suite | ✅ Strong | 19+ test files, 100+ cases |
| Docker support | ✅ Ready | Dockerfile + docker-compose |
| LLM provider abstraction | ✅ Solid | Claude/OpenAI/Gemini/Ollama/Mock |

---

## 3. What Is Missing Relative to a Career Decision Agent

### Missing: User Career Profile Depth
- No `experience_level`, `work_mode_preference`, `preferred_domains`, `company_type_preference`
- No `short_term_goal`, `long_term_goal`, `willingness_to_learn`
- No `seniority_preference`, `avoided_technologies`

### Missing: Multi-Factor Career Scoring
- Current scoring is keyword/theme-based — no seniority realism check
- No title relevance scoring (role-track match)
- No domain alignment scoring
- No work mode / location alignment
- No strategic career direction alignment
- No portfolio-to-job matching

### Missing: Recommendation Labels
- No "Apply Now", "Stretch Opportunity", "Not Worth It", etc.
- No actionable categorization beyond high/medium/low

### Missing: Gap Analysis
- No identification of what the candidate lacks per job
- No gap severity (easy/medium/hard to close)
- No "you're missing X, Y, Z for this role" output

### Missing: Action Plan Engine
- No per-job next-step recommendations
- No "update CV wording", "highlight project X", etc.

### Missing: Portfolio Project Matching
- Portfolio projects exist in `data/candidate_profile/projects.json`
- But they are never used in scoring or recommendations
- No "highlight project X for this role" logic

### Missing: Career Direction Classification
- No track classification (AI Engineer, MLOps, DevOps+AI, etc.)
- No "this job supports/distracts from your target direction"

### Missing: Feedback Loop
- No ability to record "liked/irrelevant/applied/wrong direction"
- No adaptive ranking based on feedback

### Missing: Weekly Review / Strategic Mode
- No summary of recurring missing skills
- No "focus for next 30 days" recommendations

### Missing: Decision Console UI
- Dashboard shows jobs as a list but no "decision card" per job
- No fit score breakdown visible
- No per-job recommendation + action items

---

## 4. Which Parts Should Be Preserved

- `app/collectors/` — all collectors (no changes needed)
- `app/dedup/` — dedup engine (no changes)
- `app/db/session.py` — session management (no changes)
- `app/db/normalizer.py` — normalization logic (no changes)
- `app/matching/scorer.py` — V1 keyword scorer (preserve, used by new scorer)
- `app/matching/semantic_scorer.py` — V2 semantic scorer (preserve)
- `app/matching/embedding_scorer.py` — V3 embedding scorer (preserve)
- `app/matching/combined_scorer.py` — existing combined scorer (preserve)
- `app/llm/` — all LLM providers (no changes)
- `app/notifications/` — notification system (no changes)
- `app/scheduler/` — scheduler (no changes)
- `config/sources.yaml` — source registry (no changes)
- `config/notifications.yaml` — notification config (no changes)
- All existing tests (must keep passing)

---

## 5. Which Parts Should Be Extended

| Component | Extension |
|---|---|
| `app/candidate/profile_loader.py` | Add new profile fields |
| `config/profile.yaml` | Add new profile sections |
| `app/db/models.py` | Add `CareerScore`, `JobFeedback` tables |
| `app/services/job_service.py` | Add career scoring methods |
| `dashboard/streamlit_app.py` | Add decision console tab |
| `README.md` | Rebrand as Career Decision Agent |

---

## 6. What Should NOT Be Touched Unless Necessary

- Docker/CI/CD configuration
- Test configuration (conftest.py)
- Job collection logic (collectors)
- Deduplication engine
- Notification channels
- Scheduler internals
- LLM provider implementations

---

## 7. Main Risks for Upgrade

1. **DB schema migrations:** Adding new tables/columns must not break existing data
2. **Profile backward compatibility:** New profile fields must have sensible defaults
3. **Scoring coexistence:** New career scorer must coexist with existing V1/V2/V3 scorers
4. **Dashboard complexity:** Adding more UI must not make dashboard unusable
5. **Test coverage:** New modules need tests; existing tests must still pass
6. **Import chains:** New modules must not create circular imports

---

## 8. Proposed Implementation Path

### Phase 1 — Personalized Matching Engine
1. Extend `CandidateProfile` with new career-oriented fields
2. Update `config/profile.yaml` with new sections
3. Create `app/matching/career_scorer.py` — multi-factor career decision scorer
4. Add `CareerScore` table to `app/db/models.py`
5. Integrate career scorer into `app/services/job_service.py`
6. Add recommendation labels and fit score breakdown
7. Write tests for new scorer

### Phase 2 — Decision Agent Capabilities
1. Create `app/matching/gap_analyzer.py` — gap analysis per job
2. Create `app/matching/action_planner.py` — action plan generation
3. Create `app/matching/portfolio_matcher.py` — portfolio project matching
4. Create `app/matching/career_direction.py` — career track classification
5. Wire everything into `job_service.py`
6. Add decision console output structure
7. Write tests for each module

### Phase 3 — Active Agent Features
1. Create `app/matching/weekly_review.py` — weekly review engine
2. Add `JobFeedback` table to `app/db/models.py`
3. Add feedback recording to `job_service.py`
4. Upgrade `dashboard/streamlit_app.py` with:
   - Decision Console tab
   - Fit score breakdown cards
   - Gap & action items display
   - Feedback buttons
   - Weekly review section
5. Update README.md
6. Write final documentation
