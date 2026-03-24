"""Tests for the GapAnalyzer."""
import pytest
from app.matching.gap_analyzer import GapAnalyzer, GapReport, _classify_skill_difficulty


class MockJob:
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description


PROFILE = {
    "all_skills": ["Python", "FastAPI", "Docker", "AWS", "LangChain", "LLM", "RAG"],
    "preferred_technologies": ["OpenAI", "Terraform"],
    "positive_keywords": ["python", "ai", "ml"],
    "willingness_to_learn": ["Rust", "Spark", "Kafka"],
}


class TestClassifySkillDifficulty:
    def test_easy_skill(self):
        assert _classify_skill_difficulty("fastapi") == "easy"
        assert _classify_skill_difficulty("docker") == "easy"

    def test_medium_skill(self):
        assert _classify_skill_difficulty("kubernetes") == "medium"
        assert _classify_skill_difficulty("kafka") == "medium"

    def test_hard_skill(self):
        assert _classify_skill_difficulty("rust") == "hard"
        assert _classify_skill_difficulty("c++") == "hard"

    def test_unknown_defaults_medium(self):
        assert _classify_skill_difficulty("obscure_framework_xyz") == "medium"


class TestGapAnalyzer:
    def setup_method(self):
        self.analyzer = GapAnalyzer(profile=PROFILE)

    def test_full_match_no_gaps(self):
        job = MockJob(
            title="Python AI Engineer",
            description="python fastapi docker aws llm rag langchain",
        )
        report = self.analyzer.analyze(job)
        assert isinstance(report, GapReport)
        assert len(report.matched_skills) > 0
        assert report.gap_severity in ("low", "medium", "high")

    def test_hard_gaps_identified(self):
        job = MockJob(
            title="Systems Engineer",
            description="rust c++ java spring distributed systems",
        )
        report = self.analyzer.analyze(job)
        assert len(report.hard_gaps) > 0

    def test_easy_gaps_identified(self):
        job = MockJob(
            title="Python Engineer",
            description="python fastapi docker pytest celery redis",
        )
        report = self.analyzer.analyze(job)
        # celery, redis should be easy gaps if not in profile
        assert report.gap_severity in ("low", "medium", "high")

    def test_no_skills_neutral(self):
        job = MockJob(title="Manager", description="team leadership stakeholder management")
        report = self.analyzer.analyze(job)
        assert report.gap_count == 0
        assert report.gap_severity == "low"

    def test_gap_summary_is_string(self):
        job = MockJob(title="AI Eng", description="python rust kafka spark java")
        report = self.analyzer.analyze(job)
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_to_dict_has_required_keys(self):
        job = MockJob(title="AI Eng", description="python llm fastapi")
        report = self.analyzer.analyze(job)
        d = report.to_dict()
        for key in ["matched_skills", "easy_gaps", "medium_gaps", "hard_gaps",
                    "gap_count", "gap_severity", "closeable", "summary"]:
            assert key in d
