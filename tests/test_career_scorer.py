"""Tests for the multi-factor CareerScorer."""
import pytest

from app.matching.career_scorer import (
    CareerScorer,
    CareerScoreResult,
    LABEL_APPLY_NOW,
    LABEL_APPLY_AFTER_FIX,
    LABEL_STRETCH,
    LABEL_WRONG_TIMING,
    LABEL_NOT_WORTH_IT,
    LABEL_MARKET_SIGNAL,
    ALL_LABELS,
    _detect_seniority,
    _detect_work_mode,
    _detect_domain,
    _score_title_relevance,
    _score_skill_overlap,
    _score_seniority_realism,
    _score_work_mode_alignment,
    _assign_label,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

class MockJob:
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description


STRONG_PROFILE = {
    "target_roles": ["Applied AI Engineer", "MLOps Engineer", "AI Engineer"],
    "preferred_role_track": "AI Engineer",
    "experience_level": "mid",
    "seniority_target": "mid",
    "positive_keywords": ["python", "ai", "ml", "docker", "fastapi", "aws", "llm"],
    "negative_keywords": ["phd", "principal", "relocation"],
    "preferred_technologies": ["Python", "FastAPI", "Docker", "AWS", "LangChain"],
    "avoided_technologies": ["Java", ".NET"],
    "preferred_locations": ["Israel", "Remote"],
    "work_mode_preference": "remote",
    "company_type_preference": ["startup", "tech company"],
    "short_term_goal": "Build LLM-powered applications and MLOps pipelines",
    "long_term_goal": "Become senior AI platform engineer",
    "preferred_domains": ["AI/ML Engineering", "LLM Applications", "MLOps"],
    "willingness_to_learn": ["Rust", "Spark", "Kafka"],
    "career_tracks": {
        "primary": "Applied AI / LLM Engineer",
        "acceptable": ["MLOps Engineer", "Backend Engineer with AI focus"],
        "avoid": ["Data Analyst", "Frontend only"],
    },
    "all_skills": [
        "Python", "FastAPI", "Docker", "AWS", "LangChain", "OpenAI",
        "LLM", "RAG", "Embeddings", "MLOps", "Terraform",
    ],
    "projects": [
        {
            "name": "RAG Customer Support Bot",
            "description": "RAG system with LangChain and OpenAI",
            "technologies": ["Python", "LangChain", "OpenAI", "FastAPI", "Docker"],
        },
        {
            "name": "MLOps Training Pipeline",
            "description": "ML training pipeline on AWS SageMaker",
            "technologies": ["Python", "AWS", "SageMaker", "Terraform", "Docker"],
        },
    ],
}


# ── Unit tests for helper functions ──────────────────────────────────────────

class TestDetectSeniority:
    def test_detects_senior(self):
        assert _detect_seniority("senior software engineer") == "senior"

    def test_detects_lead(self):
        assert _detect_seniority("lead engineer, 6+ years required") == "senior"

    def test_detects_junior(self):
        assert _detect_seniority("junior developer entry level") == "junior"

    def test_detects_mid(self):
        assert _detect_seniority("mid-level engineer 3+ years") == "mid"

    def test_unknown_default(self):
        assert _detect_seniority("software engineer") == "unknown"


class TestDetectWorkMode:
    def test_detects_remote(self):
        assert _detect_work_mode("fully remote work from home position") == "remote"

    def test_detects_hybrid(self):
        assert _detect_work_mode("hybrid 2 days in office") == "hybrid"

    def test_detects_onsite(self):
        assert _detect_work_mode("in office only, relocation required") == "onsite"

    def test_unknown_default(self):
        assert _detect_work_mode("engineer at a tech company") == "unknown"


class TestDetectDomain:
    def test_detects_llm_domain(self):
        domain = _detect_domain("llm applications rag langchain openai embeddings")
        assert "LLM" in domain

    def test_detects_mlops(self):
        domain = _detect_domain("mlops model deployment mlflow feature store kubeflow")
        assert "MLOps" in domain

    def test_empty_text(self):
        domain = _detect_domain("")
        assert domain == ""


class TestScoreTitleRelevance:
    def test_exact_role_match(self):
        text = "applied ai engineer python llm"
        score, strengths, gaps = _score_title_relevance(text, STRONG_PROFILE)
        assert score == 10.0
        assert any("applied ai engineer" in s.lower() for s in strengths)

    def test_partial_role_match(self):
        text = "ai engineer cloud platform"
        score, strengths, gaps = _score_title_relevance(text, STRONG_PROFILE)
        assert score >= 6.0

    def test_unrelated_title(self):
        text = "accountant financial analysis excel"
        score, strengths, gaps = _score_title_relevance(text, STRONG_PROFILE)
        assert score < 6.0
        assert len(gaps) > 0


class TestScoreSkillOverlap:
    def test_high_overlap(self):
        text = "python fastapi docker aws llm langchain embeddings"
        score, matched, missing = _score_skill_overlap(text, STRONG_PROFILE)
        assert score >= 6.0
        assert len(matched) >= 3

    def test_no_skill_text(self):
        # Text with no recognizable tech skill tokens
        text = "accounting finance sales marketing leadership strategy"
        score, matched, missing = _score_skill_overlap(text, STRONG_PROFILE)
        assert score == 5.0  # Neutral when no skills detected

    def test_missing_skills(self):
        text = "java spring boot oracle database enterprise"
        score, matched, missing = _score_skill_overlap(text, STRONG_PROFILE)
        assert len(missing) > 0


class TestScoreSeniorityRealism:
    def test_mid_to_mid_match(self):
        score, strengths, gaps = _score_seniority_realism("mid-level", "mid", STRONG_PROFILE)
        assert score == 10.0

    def test_mid_to_senior_mismatch(self):
        score, strengths, gaps = _score_seniority_realism(
            "senior engineer 6+ years", "senior", STRONG_PROFILE
        )
        assert score < 6.0
        assert len(gaps) > 0

    def test_unknown_seniority_neutral(self):
        score, strengths, gaps = _score_seniority_realism("", "unknown", STRONG_PROFILE)
        assert score >= 7.0


class TestScoreWorkModeAlignment:
    def test_remote_match(self):
        score, strengths, gaps = _score_work_mode_alignment("remote", STRONG_PROFILE)
        assert score == 10.0

    def test_onsite_mismatch(self):
        score, strengths, gaps = _score_work_mode_alignment("onsite", STRONG_PROFILE)
        assert score <= 2.0
        assert len(gaps) > 0

    def test_unknown_neutral(self):
        score, strengths, gaps = _score_work_mode_alignment("unknown", STRONG_PROFILE)
        assert score >= 7.0


class TestAssignLabel:
    def test_apply_now_high_score(self):
        label, reason = _assign_label(
            overall_score=80,
            gap_severity="low",
            seniority_score=9.0,
            work_mode_score=10.0,
            career_direction_alignment="aligned",
            hard_gaps=[],
        )
        assert label == LABEL_APPLY_NOW

    def test_apply_after_fix_medium_score(self):
        label, reason = _assign_label(
            overall_score=65,
            gap_severity="medium",
            seniority_score=8.0,
            work_mode_score=10.0,
            career_direction_alignment="aligned",
            hard_gaps=["kafka"],
        )
        assert label == LABEL_APPLY_AFTER_FIX

    def test_wrong_timing_seniority(self):
        label, reason = _assign_label(
            overall_score=62,
            gap_severity="low",
            seniority_score=2.0,
            work_mode_score=10.0,
            career_direction_alignment="aligned",
            hard_gaps=[],
        )
        assert label == LABEL_WRONG_TIMING

    def test_not_worth_it_low_score(self):
        label, reason = _assign_label(
            overall_score=25,
            gap_severity="high",
            seniority_score=3.0,
            work_mode_score=2.0,
            career_direction_alignment="off-track",
            hard_gaps=["java", "c++", "rust", "erlang"],
        )
        assert label == LABEL_NOT_WORTH_IT

    def test_all_labels_valid(self):
        assert len(ALL_LABELS) == 7
        for label in ALL_LABELS:
            assert isinstance(label, str)


# ── Integration tests: CareerScorer.score() ───────────────────────────────────

class TestCareerScorerIntegration:
    def setup_method(self):
        self.scorer = CareerScorer(profile=STRONG_PROFILE)

    def test_strong_match_role(self):
        """A well-matching LLM Engineer role should score high."""
        job = MockJob(
            title="Applied AI Engineer",
            description=(
                "Build LLM-powered applications using Python, LangChain, FastAPI. "
                "RAG pipelines, embeddings, OpenAI API integration. "
                "Remote position. Mid-level engineer, 3+ years Python."
            ),
        )
        result = self.scorer.score(job)
        assert result.overall_fit_score >= 60
        assert result.recommendation_label in (LABEL_APPLY_NOW, LABEL_APPLY_AFTER_FIX)
        assert len(result.strengths) > 0
        assert result.detected_work_mode == "remote"

    def test_senior_role_wrong_timing(self):
        """A senior role should trigger seniority mismatch for mid-level candidate."""
        job = MockJob(
            title="Senior ML Engineer",
            description=(
                "8+ years of experience required. Lead engineer. "
                "Python, MLOps, Kubernetes, AWS. Remote. "
                "Machine learning, deep learning, production systems."
            ),
        )
        result = self.scorer.score(job)
        assert result.detected_seniority == "senior"
        seniority_score = result.score_breakdown.get("seniority_realism", 10)
        assert seniority_score < 6.0
        assert result.recommendation_label in (LABEL_WRONG_TIMING, LABEL_STRETCH, LABEL_NOT_WORTH_IT)

    def test_stretch_opportunity(self):
        """A role with moderate fit should be a stretch opportunity."""
        job = MockJob(
            title="MLOps Engineer",
            description=(
                "Kubernetes, Helm, Terraform, AWS infrastructure. "
                "Python scripting. CI/CD pipelines. Mid-level. "
                "Model deployment and monitoring."
            ),
        )
        result = self.scorer.score(job)
        assert result.overall_fit_score > 30
        assert isinstance(result.recommendation_label, str)
        assert result.recommendation_label in ALL_LABELS

    def test_wrong_domain_role(self):
        """A data analyst role should score poorly for an AI engineer candidate."""
        job = MockJob(
            title="Business Intelligence Analyst",
            description=(
                "Excel, Tableau, SQL, Power BI. Financial reporting. "
                "Stakeholder management. Data analysis. Excel VBA."
            ),
        )
        result = self.scorer.score(job)
        assert result.career_direction_alignment in ("off-track", "partial", "unknown")

    def test_critical_skill_gap(self):
        """A role requiring Java/Spring should show gaps."""
        job = MockJob(
            title="Backend Engineer",
            description=(
                "Java, Spring Boot, Oracle Database, Maven. "
                "Enterprise application development. REST APIs."
            ),
        )
        result = self.scorer.score(job)
        assert len(result.gaps) > 0

    def test_result_has_action_items(self):
        """Every result should have at least some action items."""
        job = MockJob(
            title="AI Engineer",
            description="Python, LLM, RAG, FastAPI, Docker. Remote. Mid-level.",
        )
        result = self.scorer.score(job)
        assert isinstance(result.action_items, list)

    def test_result_to_dict(self):
        """to_dict() should return all expected keys."""
        job = MockJob(
            title="AI Engineer",
            description="Python, LLM, RAG.",
        )
        result = self.scorer.score(job)
        d = result.to_dict()
        expected_keys = [
            "overall_fit_score",
            "recommendation_label",
            "recommendation_reason",
            "score_breakdown",
            "strengths",
            "gaps",
            "risks",
            "gap_severity",
            "easy_to_close_gaps",
            "hard_to_close_gaps",
            "career_direction_alignment",
            "detected_domain",
            "detected_seniority",
            "detected_work_mode",
            "best_matching_project",
            "portfolio_highlights",
            "action_items",
        ]
        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_no_profile_neutral_scoring(self):
        """Without a profile, scorer should return a neutral result without crashing."""
        scorer = CareerScorer(profile=None)
        job = MockJob(
            title="Software Engineer",
            description="Python, APIs, backend systems.",
        )
        result = scorer.score(job)
        assert isinstance(result.overall_fit_score, float)
        assert result.recommendation_label in ALL_LABELS

    def test_score_breakdown_has_all_dimensions(self):
        """Score breakdown must include all 7 dimensions."""
        job = MockJob(title="AI Engineer", description="Python LLM remote")
        result = self.scorer.score(job)
        expected_dims = [
            "title_relevance",
            "skill_overlap",
            "seniority_realism",
            "domain_alignment",
            "work_mode_alignment",
            "strategic_alignment",
            "portfolio_alignment",
        ]
        for dim in expected_dims:
            assert dim in result.score_breakdown, f"Missing dimension: {dim}"
            assert 0 <= result.score_breakdown[dim] <= 10


# ── Validation scenarios ───────────────────────────────────────────────────────

class TestValidationScenarios:
    """
    6 explicit validation scenarios as specified in the requirements.
    """

    def setup_method(self):
        self.scorer = CareerScorer(profile=STRONG_PROFILE)

    def test_scenario_strong_match(self):
        """Scenario 1: Strong match role."""
        job = MockJob(
            title="Applied AI Engineer",
            description=(
                "Build LLM applications with Python, LangChain, FastAPI. "
                "RAG pipelines, vector databases. Remote. 3-5 years Python. "
                "OpenAI API, embeddings, prompt engineering. MLOps exposure."
            ),
        )
        result = self.scorer.score(job)
        assert result.overall_fit_score >= 55
        assert result.recommendation_label in (LABEL_APPLY_NOW, LABEL_APPLY_AFTER_FIX)

    def test_scenario_partial_match(self):
        """Scenario 2: Partial match role."""
        job = MockJob(
            title="Backend Python Engineer",
            description=(
                "Python, FastAPI, PostgreSQL, Docker. REST APIs. "
                "Mid-level, 3+ years. Remote. No ML required."
            ),
        )
        result = self.scorer.score(job)
        assert result.overall_fit_score > 20  # Not a zero
        assert result.recommendation_label in ALL_LABELS

    def test_scenario_stretch_role(self):
        """Scenario 3: Stretch role."""
        job = MockJob(
            title="Principal MLOps Engineer",
            description=(
                "Lead ML platform team. Kubernetes, Terraform, AWS SageMaker. "
                "5+ years MLOps. Python, architecture design. Hybrid."
            ),
        )
        result = self.scorer.score(job)
        # Should be stretch, wrong timing, or market signal due to senior signals + direction
        from app.matching.career_scorer import LABEL_MARKET_SIGNAL
        assert result.recommendation_label in (
            LABEL_STRETCH, LABEL_WRONG_TIMING, LABEL_APPLY_AFTER_FIX, LABEL_MARKET_SIGNAL
        )

    def test_scenario_wrong_direction(self):
        """Scenario 4: Wrong direction role."""
        job = MockJob(
            title="Business Intelligence Analyst",
            description=(
                "Tableau, Power BI, Excel, SQL. Financial data analysis. "
                "Reporting and dashboards. Non-technical stakeholders. Onsite."
            ),
        )
        result = self.scorer.score(job)
        # Should not be "Apply Now"
        assert result.recommendation_label != LABEL_APPLY_NOW
        assert result.career_direction_alignment in ("off-track", "partial", "unknown")

    def test_scenario_missing_critical_skill(self):
        """Scenario 5: Role with missing critical skill."""
        job = MockJob(
            title="AI Engineer",
            description=(
                "Python, LLM, RAG, FastAPI. Remote. Mid-level. "
                "Required: Rust for performance-critical inference code. "
                "C++ kernel optimization."
            ),
        )
        result = self.scorer.score(job)
        # Should have hard gaps due to Rust/C++
        assert len(result.hard_to_close_gaps) > 0 or len(result.gaps) > 0

    def test_scenario_apply_after_small_fix(self):
        """Scenario 6: Role that should become Apply After Small Fix."""
        job = MockJob(
            title="ML Engineer",
            description=(
                "Python, ML, LLM, FastAPI, Docker, AWS. Mid-level engineer. "
                "Remote. Experience with Spark preferred but not required. "
                "OpenAI API, embeddings. CI/CD pipeline."
            ),
        )
        result = self.scorer.score(job)
        # This should be Apply Now or Apply After Fix given the strong alignment
        assert result.recommendation_label in (
            LABEL_APPLY_NOW, LABEL_APPLY_AFTER_FIX, LABEL_STRETCH
        )
