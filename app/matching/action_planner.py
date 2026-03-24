"""
action_planner.py — Per-job action plan generator.

Produces concrete next steps for a candidate based on their profile,
the job's characteristics, and the gap analysis.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"


@dataclass
class ActionItem:
    """A single actionable recommendation."""
    action: str
    priority: str = PRIORITY_MEDIUM
    category: str = ""          # cv | skills | portfolio | interview | timing

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "priority": self.priority,
            "category": self.category,
        }


@dataclass
class ActionPlan:
    """Full action plan for a job application."""
    job_title: str = ""
    job_company: str = ""
    recommendation_label: str = ""

    high_priority: list[ActionItem] = field(default_factory=list)
    medium_priority: list[ActionItem] = field(default_factory=list)
    low_priority: list[ActionItem] = field(default_factory=list)

    quick_wins: list[str] = field(default_factory=list)    # 1-day actions
    short_term: list[str] = field(default_factory=list)    # 1-2 week actions
    strategic: list[str] = field(default_factory=list)     # 1+ month actions

    def all_actions(self) -> list[ActionItem]:
        return self.high_priority + self.medium_priority + self.low_priority

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_title": self.job_title,
            "job_company": self.job_company,
            "recommendation_label": self.recommendation_label,
            "high_priority": [a.to_dict() for a in self.high_priority],
            "medium_priority": [a.to_dict() for a in self.medium_priority],
            "low_priority": [a.to_dict() for a in self.low_priority],
            "quick_wins": self.quick_wins,
            "short_term": self.short_term,
            "strategic": self.strategic,
        }


class ActionPlanner:
    """
    Generates practical, prioritized action plans for job applications.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}

    def plan(
        self,
        job: Any,
        career_score_result: Any | None = None,
        gap_report: Any | None = None,
    ) -> ActionPlan:
        """
        Generate an action plan for a job.

        Args:
            job: Job ORM object with .title and .company.
            career_score_result: CareerScoreResult from CareerScorer.
            gap_report: GapReport from GapAnalyzer.
        """
        title = getattr(job, "title", "this role")
        company = getattr(job, "company", "this company")
        text = f"{title} {getattr(job, 'description', '')}".lower()

        label = ""
        overall_score = 50.0
        easy_gaps: list[str] = []
        hard_gaps: list[str] = []
        best_project = ""
        seniority_mismatch = False
        work_mode_mismatch = False

        if career_score_result is not None:
            label = getattr(career_score_result, "recommendation_label", "")
            overall_score = getattr(career_score_result, "overall_fit_score", 50.0)
            easy_gaps = getattr(career_score_result, "easy_to_close_gaps", [])
            hard_gaps = getattr(career_score_result, "hard_to_close_gaps", [])
            best_project = getattr(career_score_result, "best_matching_project", "")
            seniority_score = career_score_result.score_breakdown.get("seniority_realism", 7.0)
            work_mode_score = career_score_result.score_breakdown.get("work_mode_alignment", 7.0)
            seniority_mismatch = seniority_score < 4.5
            work_mode_mismatch = work_mode_score <= 2.0

        if gap_report is not None:
            easy_gaps = easy_gaps or getattr(gap_report, "easy_gaps", [])
            hard_gaps = hard_gaps or getattr(gap_report, "hard_gaps", [])

        plan = ActionPlan(
            job_title=title,
            job_company=company,
            recommendation_label=label,
        )

        high = []
        medium = []
        low = []

        # ── CV actions ────────────────────────────────────────────────────
        if overall_score >= 65:
            high.append(ActionItem(
                action=f"Tailor your CV to highlight experience matching '{title}' requirements.",
                priority=PRIORITY_HIGH,
                category="cv",
            ))
        else:
            medium.append(ActionItem(
                action="Review CV to ensure relevant skills are in the summary and experience sections.",
                priority=PRIORITY_MEDIUM,
                category="cv",
            ))

        # ── Portfolio actions ─────────────────────────────────────────────
        if best_project:
            high.append(ActionItem(
                action=f"Lead application with '{best_project}' — strongest portfolio match for this role.",
                priority=PRIORITY_HIGH,
                category="portfolio",
            ))
        else:
            medium.append(ActionItem(
                action="Identify which of your projects best demonstrates relevant technical skills.",
                priority=PRIORITY_MEDIUM,
                category="portfolio",
            ))

        # ── Skill gap actions ─────────────────────────────────────────────
        if easy_gaps:
            gap_list = ", ".join(easy_gaps[:3])
            medium.append(ActionItem(
                action=f"Do a quick familiarization with: {gap_list} (days-level effort).",
                priority=PRIORITY_MEDIUM,
                category="skills",
            ))

        if hard_gaps:
            gap_list = ", ".join(hard_gaps[:2])
            low.append(ActionItem(
                action=f"Add to long-term learning plan: {gap_list}.",
                priority=PRIORITY_LOW,
                category="skills",
            ))

        # ── Seniority mismatch actions ─────────────────────────────────────
        if seniority_mismatch:
            medium.append(ActionItem(
                action="Emphasize scope and impact of your past work to partially offset seniority gap.",
                priority=PRIORITY_MEDIUM,
                category="cv",
            ))
            low.append(ActionItem(
                action="Consider applying anyway with a strong cover letter explaining your trajectory.",
                priority=PRIORITY_LOW,
                category="cv",
            ))

        # ── Work mode mismatch ────────────────────────────────────────────
        if work_mode_mismatch:
            low.append(ActionItem(
                action="Clarify work mode expectations before investing time in this application.",
                priority=PRIORITY_LOW,
                category="timing",
            ))

        # ── Interview preparation ─────────────────────────────────────────
        if overall_score >= 60:
            tech_signals = _detect_tech_focus(text)
            if tech_signals:
                medium.append(ActionItem(
                    action=f"Prepare interview talking points around: {', '.join(tech_signals[:3])}.",
                    priority=PRIORITY_MEDIUM,
                    category="interview",
                ))
            medium.append(ActionItem(
                action="Prepare a 90-second pitch that connects your background to this role.",
                priority=PRIORITY_MEDIUM,
                category="interview",
            ))

        # ── Build quick_wins / short_term / strategic ─────────────────────
        plan.quick_wins = [
            a.action for a in high
            if a.category in ("cv", "portfolio")
        ][:2]

        plan.short_term = [
            a.action for a in medium
            if a.category in ("skills", "interview")
        ][:3]

        plan.strategic = [
            a.action for a in low
            if a.category == "skills"
        ][:2]

        plan.high_priority = high
        plan.medium_priority = medium
        plan.low_priority = low

        return plan


def _detect_tech_focus(text: str) -> list[str]:
    """Extract the main technical focus areas mentioned in a job posting."""
    focus_areas = {
        "LLM/RAG systems": ["llm", "rag", "langchain", "openai", "embeddings"],
        "MLOps pipelines": ["mlops", "mlflow", "kubeflow", "model serving", "sagemaker"],
        "Python backend": ["fastapi", "django", "flask", "api", "python"],
        "Cloud/Infrastructure": ["aws", "gcp", "azure", "terraform", "kubernetes"],
        "Data engineering": ["spark", "kafka", "airflow", "dbt", "pipeline"],
    }
    detected = []
    for area, keywords in focus_areas.items():
        if sum(1 for kw in keywords if kw in text) >= 2:
            detected.append(area)
    return detected
