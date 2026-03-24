"""Tests for the PortfolioMatcher."""
import pytest
from app.matching.portfolio_matcher import PortfolioMatcher, PortfolioMatchReport


class MockJob:
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description


PROFILE_WITH_PROJECTS = {
    "projects": [
        {
            "name": "RAG Customer Support Bot",
            "description": "RAG system using LangChain and OpenAI",
            "technologies": ["Python", "LangChain", "OpenAI", "FastAPI", "Docker"],
        },
        {
            "name": "MLOps Training Pipeline",
            "description": "ML training pipeline on AWS SageMaker",
            "technologies": ["Python", "AWS", "SageMaker", "Terraform", "Docker"],
        },
        {
            "name": "Data Dashboard",
            "description": "Business analytics dashboard with charts",
            "technologies": ["Python", "Pandas", "Matplotlib", "Streamlit"],
        },
    ]
}


class TestPortfolioMatcher:
    def setup_method(self):
        self.matcher = PortfolioMatcher(profile=PROFILE_WITH_PROJECTS)

    def test_returns_report(self):
        job = MockJob(title="AI Engineer", description="python llm rag langchain")
        report = self.matcher.match(job)
        assert isinstance(report, PortfolioMatchReport)

    def test_rag_role_matches_rag_project(self):
        job = MockJob(
            title="LLM Engineer",
            description="langchain openai rag embeddings python fastapi",
        )
        report = self.matcher.match(job)
        assert report.top_project == "RAG Customer Support Bot"

    def test_mlops_role_matches_mlops_project(self):
        job = MockJob(
            title="MLOps Engineer",
            description="aws sagemaker terraform mlops model deployment docker",
        )
        report = self.matcher.match(job)
        assert report.top_project == "MLOps Training Pipeline"

    def test_projects_are_ranked(self):
        job = MockJob(title="AI Engineer", description="python llm rag aws")
        report = self.matcher.match(job)
        assert len(report.project_matches) == 3
        # Check ordered by score
        scores = [m.match_score for m in report.project_matches]
        assert scores == sorted(scores, reverse=True)

    def test_highlight_order_set(self):
        job = MockJob(title="AI Engineer", description="python llm")
        report = self.matcher.match(job)
        orders = [m.highlight_order for m in report.project_matches]
        assert orders == [1, 2, 3]

    def test_recommendation_is_string(self):
        job = MockJob(title="Engineer", description="python")
        report = self.matcher.match(job)
        assert isinstance(report.recommendation, str)
        assert len(report.recommendation) > 0

    def test_no_projects_returns_report(self):
        matcher = PortfolioMatcher(profile={})
        job = MockJob(title="AI Engineer", description="python")
        report = matcher.match(job)
        assert isinstance(report, PortfolioMatchReport)
        assert report.top_project == ""

    def test_to_dict_complete(self):
        job = MockJob(title="AI Engineer", description="python llm")
        report = self.matcher.match(job)
        d = report.to_dict()
        for key in ["job_title", "project_matches", "top_project", "recommendation", "emphasis_advice"]:
            assert key in d
