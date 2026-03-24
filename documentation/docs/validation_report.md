# Validation Report — Career Decision Agent V2

**Date:** 2026-03-24
**Branch:** feature/career-decision-agent-v2

---

## 1. Tests Run

### Full Test Suite

```
455 passed, 213 warnings in 22.59s
0 failures
```

**Total tests:** 455
**New tests added:** 76
**Pre-existing tests:** 379

### New Tests by Module

| File | Tests | Status |
|---|---|---|
| `tests/test_career_scorer.py` | 44 | ✅ All pass |
| `tests/test_gap_analyzer.py` | 10 | ✅ All pass |
| `tests/test_career_direction.py` | 7 | ✅ All pass |
| `tests/test_action_planner.py` | 7 | ✅ All pass |
| `tests/test_portfolio_matcher.py` | 8 | ✅ All pass |

---

## 2. Validation Scenarios

The following 6 explicit scenarios were validated in `TestValidationScenarios`:

### Scenario 1: Strong Match Role
**Input:** Applied AI Engineer role with LLM, LangChain, FastAPI, RAG, Docker, remote, mid-level

**Expected:** `overall_fit_score >= 55`, label ∈ {Apply Now, Apply After Small Fix}

**Result:** ✅ Passed — score in expected range, label correct

---

### Scenario 2: Partial Match Role
**Input:** Backend Python Engineer — Python, FastAPI, PostgreSQL, no ML required

**Expected:** Score > 20 (not zero), valid label

**Result:** ✅ Passed — partial skill overlap detected, valid label assigned

---

### Scenario 3: Stretch Role
**Input:** Principal MLOps Engineer — 5+ years, Kubernetes, Terraform, SageMaker, Hybrid

**Expected:** Label ∈ {Stretch, Wrong Timing, Apply After Fix, Market Signal Only}

**Result:** ✅ Passed — seniority mismatch detected (senior signals vs mid candidate), Market Signal due to domain direction

---

### Scenario 4: Wrong Direction Role
**Input:** Business Intelligence Analyst — Tableau, Excel, SQL, Power BI, Onsite

**Expected:** `career_direction_alignment` ∈ {off-track, partial, unknown}

**Result:** ✅ Passed — domain not detected (Tableau/BI not in domain vocabulary), direction = "unknown" which is not "aligned"

---

### Scenario 5: Role with Missing Critical Skill
**Input:** AI Engineer — Python, LLM, but also requires Rust for inference code and C++ optimization

**Expected:** `hard_to_close_gaps` non-empty OR gaps non-empty

**Result:** ✅ Passed — Rust and C++ identified as hard gaps

---

### Scenario 6: Apply After Small Fix
**Input:** ML Engineer — Python, ML, LLM, FastAPI, Docker, AWS, remote, mid-level (Spark preferred not required)

**Expected:** Label ∈ {Apply Now, Apply After Small Fix, Stretch}

**Result:** ✅ Passed — strong skill and domain alignment detected

---

## 3. End-to-End Smoke Test

```
Profile loaded: ['Applied AI Engineer', 'MLOps Engineer'] ...
Experience level: mid
Work mode pref: remote
Collected: {'collected': 15, 'inserted': 15, 'skipped': 0, 'errors': 0}
Career scored: 15 jobs
Jobs with career scores: 15
Top job: LLM Platform Engineer
Fit score: 86.9
Label: Apply Now
Career summary: {
  'total_jobs': 15,
  'career_scored': 15,
  'label_counts': {
    'Apply Now': 8,
    'Apply After Small Fix': 2,
    'Stretch Opportunity': 3,
    'Good Role, Wrong Timing': 0,
    'Good Company, Wrong Role': 1,
    'Not Worth It': 0,
    'Market Signal Only': 1
  },
  'avg_fit_score': 72.2
}
```

**Result:** ✅ Pipeline works end-to-end

---

## 4. Unit Test Coverage

### CareerScorer
- Seniority detection (senior/junior/mid/unknown) ✅
- Work mode detection (remote/hybrid/onsite/unknown) ✅
- Domain detection (LLM Applications, MLOps, Backend, etc.) ✅
- Title relevance scoring (exact match, partial match, no match) ✅
- Skill overlap scoring (high overlap, no skills, missing skills) ✅
- Seniority realism scoring (mid-to-mid, mid-to-senior, unknown) ✅
- Work mode alignment scoring (match, mismatch, unknown) ✅
- Label assignment (Apply Now, Apply After Fix, Wrong Timing, Not Worth It) ✅
- Integration: strong match, senior role, stretch, wrong domain, critical gap ✅
- All 7 score dimensions in breakdown ✅
- No-profile neutral scoring ✅
- `to_dict()` has all required keys ✅

### GapAnalyzer
- Skill difficulty classification (easy/medium/hard) ✅
- Full match no gaps ✅
- Hard gaps identified (Rust, C++) ✅
- Easy gaps identified (pytest, celery, redis) ✅
- No skills detected → neutral ✅
- Summary string generation ✅
- `to_dict()` structure ✅

### CareerDirectionAnalyzer
- LLM role → aligned ✅
- Data analyst → off-track / distraction ✅
- MLOps → acceptable/partial ✅
- Detected track is non-empty ✅
- Advice is present ✅
- `to_dict()` complete ✅
- No profile → no crash ✅

### ActionPlanner
- Returns ActionPlan ✅
- Apply Now → high priority actions ✅
- Apply After Fix → gap closing actions ✅
- Quick wins populated ✅
- to_dict() structure ✅
- No career score → no crash ✅
- Action items are strings ✅

### PortfolioMatcher
- RAG role → RAG project first ✅
- MLOps role → MLOps project first ✅
- Projects ranked by score ✅
- Highlight order set ✅
- Recommendation is a string ✅
- No projects → no crash ✅
- `to_dict()` complete ✅

---

## 5. Known Limitations

### Partially Tested (Functional, Not Fully Unit-Tested)
- `weekly_review.py` — integration tested via smoke test, no dedicated unit tests written
- Dashboard UI — not programmatically verified (requires Streamlit test runner)
- Feedback recording — tested via service layer unit tests, not via UI
- `career_direction.py` transition path detection — basic tests written, edge cases not exhaustive

### Not Yet Tested
- DB migration behavior on existing production databases with pre-V2 data
  - New tables (`career_scores`, `job_feedback`) are appended by `init_db()` without affecting existing data
  - Verified by smoke test but not by explicit migration test

### Not Implemented (Future Work)
- Feedback-based ranking adaptation (feedback is recorded but not yet used to rerank jobs)
- Multi-user / multi-profile support
- LLM-enhanced gap analysis (current approach is rule-based)
- Real-time job freshness scoring

---

## 6. Pre-existing Test Regression

All 379 pre-existing tests continue to pass after the upgrade:
- test_scoring.py, test_semantic_scoring.py, test_embedding_scorer.py ✅
- test_filtering.py, test_dedup_engine.py ✅
- test_collectors.py, test_israel_collectors.py ✅
- test_database.py ✅
- test_notifications.py ✅
- test_llm_providers.py ✅
- test_scheduler.py, test_dashboard.py ✅
- test_candidate_profile.py ✅
- All other existing tests ✅
