"""Tests for the ActionPlanner."""
import pytest
from app.matching.action_planner import ActionPlanner, ActionPlan, ActionItem, PRIORITY_HIGH


class MockJob:
    def __init__(self, title: str, company: str = "TestCo", description: str = ""):
        self.title = title
        self.company = company
        self.description = description


class MockCareerScore:
    def __init__(
        self,
        label: str = "Apply Now",
        score: float = 75.0,
        easy_gaps: list = None,
        hard_gaps: list = None,
        best_project: str = "My Project",
    ):
        self.recommendation_label = label
        self.overall_fit_score = score
        self.easy_to_close_gaps = easy_gaps or []
        self.hard_to_close_gaps = hard_gaps or []
        self.best_matching_project = best_project
        self.score_breakdown = {
            "seniority_realism": 8.0,
            "work_mode_alignment": 9.0,
        }


PROFILE = {
    "target_roles": ["AI Engineer"],
    "preferred_technologies": ["Python", "FastAPI"],
}


class TestActionPlanner:
    def setup_method(self):
        self.planner = ActionPlanner(profile=PROFILE)

    def test_plan_returns_action_plan(self):
        job = MockJob(title="AI Engineer", description="python llm fastapi")
        career_score = MockCareerScore(label="Apply Now", score=80.0)
        plan = self.planner.plan(job, career_score_result=career_score)
        assert isinstance(plan, ActionPlan)

    def test_apply_now_has_high_priority_actions(self):
        job = MockJob(title="AI Engineer", description="python llm fastapi remote")
        career_score = MockCareerScore(label="Apply Now", score=82.0, best_project="RAG Bot")
        plan = self.planner.plan(job, career_score_result=career_score)
        assert len(plan.high_priority) > 0

    def test_apply_after_fix_includes_gap_actions(self):
        job = MockJob(title="ML Engineer", description="python ml llm kafka spark")
        career_score = MockCareerScore(
            label="Apply After Small Fix",
            score=65.0,
            easy_gaps=["kafka", "spark"],
        )
        plan = self.planner.plan(job, career_score_result=career_score)
        # Should have medium actions addressing gaps
        all_text = " ".join(a.action for a in plan.medium_priority)
        assert "kafka" in all_text.lower() or "spark" in all_text.lower()

    def test_plan_has_quick_wins(self):
        job = MockJob(title="AI Engineer", description="python llm")
        career_score = MockCareerScore(label="Apply Now", score=80.0, best_project="RAG Bot")
        plan = self.planner.plan(job, career_score_result=career_score)
        assert isinstance(plan.quick_wins, list)

    def test_to_dict_structure(self):
        job = MockJob(title="AI Engineer")
        plan = self.planner.plan(job)
        d = plan.to_dict()
        for key in ["job_title", "job_company", "high_priority", "medium_priority",
                    "low_priority", "quick_wins", "short_term", "strategic"]:
            assert key in d

    def test_no_crash_without_career_score(self):
        job = MockJob(title="AI Engineer")
        plan = self.planner.plan(job, career_score_result=None)
        assert isinstance(plan, ActionPlan)

    def test_action_items_are_strings(self):
        job = MockJob(title="AI Engineer", description="python ml")
        plan = self.planner.plan(job)
        for item in plan.all_actions():
            assert isinstance(item.action, str)
            assert len(item.action) > 0
