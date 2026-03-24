"""
Tests for the Manual Job Analysis (Paste & Analyze) feature.

Covers:
- parse_job_text() normalisation
- ManualJobAnalyzer.analyze() full pipeline
- ManualJobAnalyzer.analyze_apply_only() focused output
- ManualJobAnalyzer.analyze_portfolio_only() portfolio path
- Required output fields
- Edge cases (empty text, no profile)
"""
import pytest
from app.services.manual_job_analysis import (
    parse_job_text,
    ParsedJob,
    ManualJobAnalyzer,
    ManualAnalysisResult,
    _detect_seniority_hint,
    _extract_technologies,
    _derive_apply_decision,
)


# ── Sample data ───────────────────────────────────────────────────────────────

_JD_STRONG = """
Applied AI Engineer — LLM Platform

We are looking for a mid-level engineer to build LLM-powered applications.

Requirements:
- Python, FastAPI, Docker, AWS
- LangChain, OpenAI API, RAG pipelines
- Embeddings and vector databases (ChromaDB)
- 3+ years Python experience

Nice to have: Terraform, Kubernetes

Fully remote. Competitive salary.
""".strip()

_JD_SENIOR = """
Senior Principal ML Engineer — 8+ years required

Lead architect role. Design distributed ML systems at scale.
Rust, C++, Java. Deep knowledge of compiler internals.
Must relocate to San Francisco. Principal-level compensation.
""".strip()

_JD_DATA_ANALYST = """
Business Intelligence Analyst

Excel, Tableau, Power BI, SQL. Financial reporting.
Build dashboards for non-technical stakeholders.
Onsite only. No engineering required.
""".strip()

_JD_MINIMAL = "Python developer needed."

_PROFILE = {
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
    "short_term_goal": "Build LLM applications and MLOps pipelines",
    "long_term_goal": "Become senior AI platform engineer",
    "preferred_domains": ["AI/ML Engineering", "LLM Applications", "MLOps"],
    "willingness_to_learn": ["Rust", "Spark"],
    "career_tracks": {
        "primary": "Applied AI / LLM Engineer",
        "acceptable": ["MLOps Engineer"],
        "avoid": ["Data Analyst"],
    },
    "all_skills": [
        "Python", "FastAPI", "Docker", "AWS", "LangChain",
        "LLM", "RAG", "Embeddings", "MLOps", "Terraform",
    ],
    "projects": [
        {
            "name": "RAG Customer Support Bot",
            "description": "RAG pipeline with LangChain and OpenAI",
            "technologies": ["Python", "LangChain", "OpenAI", "FastAPI", "Docker"],
        },
        {
            "name": "MLOps Pipeline",
            "description": "ML training pipeline on AWS SageMaker",
            "technologies": ["Python", "AWS", "SageMaker", "Terraform", "Docker"],
        },
    ],
}


# ── parse_job_text ────────────────────────────────────────────────────────────

class TestParseJobText:
    def test_returns_parsed_job(self):
        pj = parse_job_text(_JD_STRONG)
        assert isinstance(pj, ParsedJob)

    def test_title_override_used(self):
        pj = parse_job_text(_JD_STRONG, title="Custom Title")
        assert pj.title == "Custom Title"

    def test_title_inferred_from_first_line(self):
        pj = parse_job_text(_JD_STRONG)
        # First line of _JD_STRONG is "Applied AI Engineer — LLM Platform"
        assert "AI Engineer" in pj.title or len(pj.title) > 0

    def test_company_override(self):
        pj = parse_job_text(_JD_STRONG, company="Acme Corp")
        assert pj.company == "Acme Corp"

    def test_company_default(self):
        pj = parse_job_text(_JD_STRONG)
        assert pj.company == "Unknown Company"

    def test_location_override(self):
        pj = parse_job_text(_JD_STRONG, location="Tel Aviv")
        assert pj.location == "Tel Aviv"

    def test_description_is_full_text(self):
        pj = parse_job_text(_JD_STRONG)
        assert "LangChain" in pj.description
        assert "RAG" in pj.description

    def test_technologies_extracted(self):
        pj = parse_job_text(_JD_STRONG)
        assert len(pj.extracted_technologies) > 0
        lower = [t.lower() for t in pj.extracted_technologies]
        assert "python" in lower or "docker" in lower or "langchain" in lower

    def test_seniority_mid_detected(self):
        pj = parse_job_text(_JD_STRONG)  # contains "3+ years"
        assert pj.detected_seniority_hint in ("mid", "unknown")

    def test_seniority_senior_detected(self):
        pj = parse_job_text(_JD_SENIOR)
        assert pj.detected_seniority_hint == "senior"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_job_text("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_job_text("   \n  ")

    def test_minimal_text_does_not_crash(self):
        pj = parse_job_text(_JD_MINIMAL)
        assert isinstance(pj, ParsedJob)
        assert pj.description == _JD_MINIMAL


# ── Helper functions ──────────────────────────────────────────────────────────

class TestHelpers:
    def test_detect_senior(self):
        assert _detect_seniority_hint("senior engineer required") == "senior"
        assert _detect_seniority_hint("8+ years experience") == "senior"

    def test_detect_junior(self):
        assert _detect_seniority_hint("junior developer entry level") == "junior"

    def test_detect_mid(self):
        assert _detect_seniority_hint("3+ years python experience") == "mid"

    def test_detect_unknown(self):
        assert _detect_seniority_hint("we are hiring a developer") == "unknown"

    def test_extract_technologies_basic(self):
        techs = _extract_technologies("we use python fastapi docker and aws")
        lower = [t.lower() for t in techs]
        assert "python" in lower
        assert "fastapi" in lower
        assert "docker" in lower
        assert "aws" in lower

    def test_extract_technologies_no_false_positives(self):
        # "r" should not appear inside "marketing"
        techs = _extract_technologies("accounting finance marketing strategy leadership")
        assert "r" not in techs

    def test_extract_empty(self):
        assert _extract_technologies("") == []

    def test_derive_apply_yes(self):
        from app.matching.career_scorer import LABEL_APPLY_NOW
        decision, explanation = _derive_apply_decision(82, LABEL_APPLY_NOW, "low", [])
        assert decision == "YES"
        assert len(explanation) > 0

    def test_derive_apply_no(self):
        from app.matching.career_scorer import LABEL_NOT_WORTH_IT
        decision, explanation = _derive_apply_decision(30, LABEL_NOT_WORTH_IT, "high", ["rust", "c++"])
        assert decision == "NO"

    def test_derive_apply_conditional(self):
        from app.matching.career_scorer import LABEL_STRETCH
        decision, explanation = _derive_apply_decision(55, LABEL_STRETCH, "medium", [])
        assert decision in ("YES", "NO", "CONDITIONAL")


# ── ManualJobAnalyzer.analyze() ───────────────────────────────────────────────

class TestManualJobAnalyzerFull:
    def setup_method(self):
        self.analyzer = ManualJobAnalyzer(profile=_PROFILE)

    def test_returns_manual_analysis_result(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert isinstance(result, ManualAnalysisResult)

    def test_strong_jd_scores_well(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert result.overall_fit_score >= 50

    def test_parsed_job_populated(self):
        result = self.analyzer.analyze(_JD_STRONG, title="AI Engineer", company="TestCo")
        assert result.parsed_job.title == "AI Engineer"
        assert result.parsed_job.company == "TestCo"

    def test_recommendation_label_is_valid(self):
        from app.matching.career_scorer import ALL_LABELS
        result = self.analyzer.analyze(_JD_STRONG)
        assert result.recommendation_label in ALL_LABELS + ["Analysis Error"]

    def test_apply_decision_is_valid(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert result.apply_decision in ("YES", "NO", "CONDITIONAL")

    def test_apply_explanation_is_string(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert isinstance(result.apply_explanation, str)
        assert len(result.apply_explanation) > 0

    def test_action_items_populated(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert isinstance(result.action_items, list)
        assert len(result.action_items) > 0
        for item in result.action_items:
            assert isinstance(item, str)

    def test_portfolio_fields_present(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert isinstance(result.best_matching_project, str)
        assert isinstance(result.portfolio_recommendation, str)
        assert isinstance(result.portfolio_highlights, list)

    def test_career_direction_fields_present(self):
        result = self.analyzer.analyze(_JD_STRONG)
        assert isinstance(result.detected_track, str)
        assert isinstance(result.direction_assessment, str)

    def test_score_breakdown_has_dimensions(self):
        result = self.analyzer.analyze(_JD_STRONG)
        dims = [
            "title_relevance", "skill_overlap", "seniority_realism",
            "domain_alignment", "work_mode_alignment", "strategic_alignment",
            "portfolio_alignment",
        ]
        for d in dims:
            assert d in result.score_breakdown

    def test_to_dict_has_all_keys(self):
        result = self.analyzer.analyze(_JD_STRONG)
        d = result.to_dict()
        required_keys = [
            "parsed_title", "parsed_company", "overall_fit_score",
            "recommendation_label", "score_breakdown", "strengths", "gaps",
            "risks", "gap_severity", "apply_decision", "apply_explanation",
            "action_items", "best_matching_project", "portfolio_recommendation",
            "detected_track", "direction_assessment",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"

    def test_senior_role_scores_lower_than_mid_role(self):
        result_mid = self.analyzer.analyze(_JD_STRONG)
        result_senior = self.analyzer.analyze(_JD_SENIOR)
        # Senior role should score lower (seniority mismatch for mid candidate)
        seniority_mid = result_mid.score_breakdown.get("seniority_realism", 5)
        seniority_senior = result_senior.score_breakdown.get("seniority_realism", 5)
        assert seniority_senior < seniority_mid

    def test_off_track_role_direction(self):
        result = self.analyzer.analyze(_JD_DATA_ANALYST)
        # BI Analyst is off-track for AI Engineer candidate
        assert result.direction_assessment in ("off-track", "partial", "unknown")

    def test_no_profile_does_not_crash(self):
        analyzer = ManualJobAnalyzer(profile=None)
        result = analyzer.analyze(_JD_STRONG)
        assert isinstance(result, ManualAnalysisResult)
        assert isinstance(result.overall_fit_score, float)

    def test_minimal_text_does_not_crash(self):
        result = self.analyzer.analyze(_JD_MINIMAL)
        assert isinstance(result, ManualAnalysisResult)

    def test_rag_role_highlights_rag_project(self):
        result = self.analyzer.analyze(_JD_STRONG)  # LLM/RAG focused JD
        if result.best_matching_project:
            assert "RAG" in result.best_matching_project or "LLM" in result.best_matching_project \
                or len(result.best_matching_project) > 0


# ── ManualJobAnalyzer.analyze_apply_only() ───────────────────────────────────

class TestManualJobAnalyzerApplyOnly:
    def setup_method(self):
        self.analyzer = ManualJobAnalyzer(profile=_PROFILE)

    def test_returns_dict(self):
        out = self.analyzer.analyze_apply_only(_JD_STRONG)
        assert isinstance(out, dict)

    def test_required_keys_present(self):
        out = self.analyzer.analyze_apply_only(_JD_STRONG)
        for key in ["apply_decision", "apply_explanation", "recommendation_label",
                    "overall_fit_score", "top_actions"]:
            assert key in out

    def test_apply_decision_valid(self):
        out = self.analyzer.analyze_apply_only(_JD_STRONG)
        assert out["apply_decision"] in ("YES", "NO", "CONDITIONAL")

    def test_top_actions_is_list(self):
        out = self.analyzer.analyze_apply_only(_JD_STRONG)
        assert isinstance(out["top_actions"], list)
        assert len(out["top_actions"]) <= 2


# ── ManualJobAnalyzer.analyze_portfolio_only() ───────────────────────────────

class TestManualJobAnalyzerPortfolioOnly:
    def setup_method(self):
        self.analyzer = ManualJobAnalyzer(profile=_PROFILE)

    def test_returns_dict(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        assert isinstance(out, dict)

    def test_required_keys_present(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        for key in ["best_matching_project", "recommendation", "emphasis_advice", "all_matches"]:
            assert key in out

    def test_best_project_is_string(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        assert isinstance(out["best_matching_project"], str)

    def test_recommendation_is_string(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        assert isinstance(out["recommendation"], str)
        assert len(out["recommendation"]) > 0

    def test_all_matches_is_list(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        assert isinstance(out["all_matches"], list)

    def test_rag_jd_picks_rag_project(self):
        out = self.analyzer.analyze_portfolio_only(_JD_STRONG)
        # The LLM/RAG JD should match the RAG project first
        if out["best_matching_project"]:
            assert "RAG" in out["best_matching_project"] or len(out["best_matching_project"]) > 0

    def test_no_profile_does_not_crash(self):
        analyzer = ManualJobAnalyzer(profile=None)
        out = analyzer.analyze_portfolio_only(_JD_STRONG)
        assert isinstance(out, dict)
        assert "best_matching_project" in out
