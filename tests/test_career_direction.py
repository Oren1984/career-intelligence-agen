"""Tests for the CareerDirectionAnalyzer."""
import pytest
from app.matching.career_direction import (
    CareerDirectionAnalyzer,
    CareerDirectionResult,
    TRACK_AI_ENGINEER,
    TRACK_MLOPS,
    TRACK_DATA_ENGINEER,
    TRACK_BACKEND,
    DIRECTION_ALIGNED,
    DIRECTION_OFF_TRACK,
    DIRECTION_PARTIAL,
    DIRECTION_TRANSITION,
)


class MockJob:
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description


PROFILE = {
    "career_tracks": {
        "primary": "Applied AI / LLM Engineer",
        "acceptable": ["MLOps Engineer", "Backend Engineer with AI focus"],
        "avoid": ["Data Analyst", "Frontend only"],
    },
    "preferred_domains": ["AI/ML Engineering", "LLM Applications", "MLOps"],
}


class TestCareerDirectionAnalyzer:
    def setup_method(self):
        self.analyzer = CareerDirectionAnalyzer(profile=PROFILE)

    def test_llm_role_is_aligned(self):
        job = MockJob(
            title="LLM Engineer",
            description="llm rag langchain openai embeddings ai engineer python fastapi",
        )
        result = self.analyzer.analyze(job)
        assert result.direction_assessment in (DIRECTION_ALIGNED, DIRECTION_PARTIAL)
        assert result.supports_primary_goal or result.direction_assessment != DIRECTION_OFF_TRACK

    def test_data_analyst_is_off_track(self):
        job = MockJob(
            title="Data Analyst",
            description="data analyst excel tableau sql reporting business intelligence stakeholder",
        )
        result = self.analyzer.analyze(job)
        assert result.is_distraction

    def test_mlops_is_acceptable(self):
        job = MockJob(
            title="MLOps Engineer",
            description="mlops mlflow kubeflow model deployment feature store kubernetes",
        )
        result = self.analyzer.analyze(job)
        assert result.direction_assessment in (DIRECTION_PARTIAL, DIRECTION_ALIGNED, DIRECTION_TRANSITION)

    def test_result_has_detected_track(self):
        job = MockJob(
            title="Data Engineer",
            description="spark kafka airflow etl dbt snowflake data pipeline",
        )
        result = self.analyzer.analyze(job)
        assert isinstance(result.detected_track, str)
        assert result.detected_track != ""

    def test_result_has_advice(self):
        job = MockJob(title="AI Engineer", description="llm python fastapi")
        result = self.analyzer.analyze(job)
        assert isinstance(result.advice, str)

    def test_to_dict_complete(self):
        job = MockJob(title="AI Engineer", description="python llm rag")
        result = self.analyzer.analyze(job)
        d = result.to_dict()
        expected_keys = [
            "detected_track", "track_confidence", "track_scores",
            "direction_assessment", "direction_explanation",
            "supports_primary_goal", "is_transition_role",
            "is_distraction", "advice",
        ]
        for key in expected_keys:
            assert key in d

    def test_no_profile_does_not_crash(self):
        analyzer = CareerDirectionAnalyzer(profile=None)
        job = MockJob(title="Engineer", description="python backend api")
        result = analyzer.analyze(job)
        assert isinstance(result, CareerDirectionResult)
