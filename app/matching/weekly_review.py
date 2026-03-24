"""
weekly_review.py — Weekly / strategic review mode.

Summarizes top opportunities, recurring skill gaps, strongest directions,
and suggested focus areas for the next 7-30 days.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WeeklyReviewReport:
    """Strategic weekly review output."""

    # Top opportunities this cycle
    top_opportunities: list[dict[str, Any]] = field(default_factory=list)
    apply_now_count: int = 0
    stretch_count: int = 0

    # Skill trends
    recurring_missing_skills: list[tuple[str, int]] = field(default_factory=list)  # (skill, freq)
    strongest_skills: list[str] = field(default_factory=list)

    # Direction insights
    strongest_job_direction: str = ""
    direction_distribution: dict[str, int] = field(default_factory=dict)

    # Patterns to ignore
    low_value_patterns: list[str] = field(default_factory=list)

    # Focus recommendations
    focus_next_7_days: list[str] = field(default_factory=list)
    focus_next_30_days: list[str] = field(default_factory=list)

    # Summary text
    executive_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "top_opportunities": self.top_opportunities,
            "apply_now_count": self.apply_now_count,
            "stretch_count": self.stretch_count,
            "recurring_missing_skills": self.recurring_missing_skills,
            "strongest_skills": self.strongest_skills,
            "strongest_job_direction": self.strongest_job_direction,
            "direction_distribution": self.direction_distribution,
            "low_value_patterns": self.low_value_patterns,
            "focus_next_7_days": self.focus_next_7_days,
            "focus_next_30_days": self.focus_next_30_days,
            "executive_summary": self.executive_summary,
        }


class WeeklyReviewEngine:
    """
    Generates a strategic weekly review from accumulated job scoring results.

    Accepts a list of job records (dicts) that include career_score data,
    or a list of (job, career_score_result) tuples.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}

    def generate(self, job_records: list[dict[str, Any]]) -> WeeklyReviewReport:
        """
        Generate a weekly review from a list of job records.

        Each record should have at minimum:
          - title, company
          - overall_fit_score
          - recommendation_label
          - gaps (list of str)
          - detected_track (str)
          - score_breakdown (dict)
        """
        if not job_records:
            return WeeklyReviewReport(
                executive_summary="No job data available for review."
            )

        report = WeeklyReviewReport()

        # ── Top opportunities ──────────────────────────────────────────────
        from app.matching.career_scorer import (
            LABEL_APPLY_NOW,
            LABEL_APPLY_AFTER_FIX,
            LABEL_STRETCH,
            LABEL_WRONG_TIMING,
            LABEL_NOT_WORTH_IT,
        )

        apply_now = [
            r for r in job_records
            if r.get("recommendation_label") == LABEL_APPLY_NOW
        ]
        apply_fix = [
            r for r in job_records
            if r.get("recommendation_label") == LABEL_APPLY_AFTER_FIX
        ]
        stretch = [
            r for r in job_records
            if r.get("recommendation_label") == LABEL_STRETCH
        ]

        # Sort by overall_fit_score
        top = sorted(
            apply_now + apply_fix,
            key=lambda r: r.get("overall_fit_score", 0),
            reverse=True,
        )[:5]

        report.top_opportunities = [
            {
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "fit_score": r.get("overall_fit_score", 0),
                "label": r.get("recommendation_label", ""),
            }
            for r in top
        ]
        report.apply_now_count = len(apply_now)
        report.stretch_count = len(stretch)

        # ── Missing skills frequency ───────────────────────────────────────
        all_gaps: list[str] = []
        for r in job_records:
            gaps = r.get("gaps", [])
            if isinstance(gaps, list):
                # Extract skill names from gap strings
                for gap in gaps:
                    if "missing skills:" in gap.lower():
                        skills_part = gap.lower().split("missing skills:")[1]
                        skills = [s.strip() for s in skills_part.split(",")]
                        all_gaps.extend(skills)
                    elif "easy_gaps" in r:
                        all_gaps.extend(r.get("easy_gaps", []))
                    elif "hard_gaps" in r:
                        all_gaps.extend(r.get("hard_gaps", []))

        skill_counter = Counter(all_gaps)
        report.recurring_missing_skills = skill_counter.most_common(8)

        # ── Strongest skills (from matched) ───────────────────────────────
        all_matched: list[str] = []
        for r in job_records:
            breakdown = r.get("score_breakdown", {})
            if isinstance(breakdown, dict):
                skill_score = breakdown.get("skill_overlap", 0)
                if skill_score >= 7.0:
                    strengths = r.get("strengths", [])
                    for s in strengths:
                        if "skill overlap" in s.lower():
                            # Extract skill names from strength string
                            parts = s.split(":")
                            if len(parts) > 1:
                                skills = [sk.strip() for sk in parts[1].split(",")]
                                all_matched.extend(skills)

        strongest_counter = Counter(all_matched)
        report.strongest_skills = [s for s, _ in strongest_counter.most_common(5)]

        # ── Direction distribution ─────────────────────────────────────────
        direction_counts: dict[str, int] = {}
        for r in job_records:
            track = r.get("detected_track") or r.get("detected_domain", "Other")
            direction_counts[track] = direction_counts.get(track, 0) + 1

        report.direction_distribution = direction_counts

        # Best direction = highest count from "good" jobs
        good_directions: dict[str, int] = {}
        for r in job_records:
            if r.get("overall_fit_score", 0) >= 55:
                track = r.get("detected_track") or r.get("detected_domain", "Other")
                good_directions[track] = good_directions.get(track, 0) + 1

        if good_directions:
            report.strongest_job_direction = max(good_directions, key=good_directions.get)  # type: ignore

        # ── Low value patterns ─────────────────────────────────────────────
        low_value = [
            r for r in job_records
            if r.get("recommendation_label") in (LABEL_NOT_WORTH_IT,)
            or r.get("overall_fit_score", 100) < 35
        ]
        if len(low_value) >= 3:
            # Find common characteristics
            low_titles = [r.get("title", "") for r in low_value]
            low_title_words = []
            for t in low_titles:
                low_title_words.extend(t.lower().split())
            word_freq = Counter(w for w in low_title_words if len(w) > 3)
            common_words = [w for w, _ in word_freq.most_common(3)]
            if common_words:
                report.low_value_patterns = [
                    f"Jobs with '{w}' in title tend to score poorly for your profile"
                    for w in common_words[:2]
                ]

        # ── Focus recommendations ──────────────────────────────────────────
        report.focus_next_7_days = self._build_7_day_focus(
            apply_now, apply_fix, report.recurring_missing_skills
        )
        report.focus_next_30_days = self._build_30_day_focus(
            stretch, report.recurring_missing_skills, report.strongest_job_direction
        )

        # ── Executive summary ──────────────────────────────────────────────
        report.executive_summary = self._build_summary(report, len(job_records))

        return report

    def _build_7_day_focus(
        self,
        apply_now: list,
        apply_fix: list,
        missing_skills: list[tuple[str, int]],
    ) -> list[str]:
        focus = []
        if apply_now:
            focus.append(
                f"Apply to {len(apply_now)} 'Apply Now' job(s) — these are your best current opportunities."
            )
        if apply_fix:
            focus.append(
                f"Prepare targeted applications for {len(apply_fix)} 'Apply After Fix' jobs."
            )
        if missing_skills:
            top_skill = missing_skills[0][0]
            focus.append(f"Quick skill refresh on '{top_skill}' — it keeps appearing in good jobs.")
        if not focus:
            focus.append("Review new job postings and update your profile with recent work.")
        return focus[:3]

    def _build_30_day_focus(
        self,
        stretch_roles: list,
        missing_skills: list[tuple[str, int]],
        direction: str,
    ) -> list[str]:
        focus = []
        if missing_skills:
            top_2 = [s for s, _ in missing_skills[:2]]
            focus.append(
                f"Build or document experience in: {', '.join(top_2)} — "
                f"these gaps appear across multiple relevant roles."
            )
        if direction:
            focus.append(
                f"Focus applications on '{direction}' roles — "
                f"your profile fits best in this direction."
            )
        if stretch_roles:
            focus.append(
                f"Invest in a project that closes gaps for stretch roles "
                f"({len(stretch_roles)} identified)."
            )
        if not focus:
            focus.append("Expand job search sources and collect more data for better insights.")
        return focus[:3]

    def _build_summary(self, report: WeeklyReviewReport, total: int) -> str:
        parts = [f"Weekly Review — {total} jobs analyzed."]

        if report.apply_now_count:
            parts.append(f"{report.apply_now_count} job(s) ready to apply to now.")
        if report.stretch_count:
            parts.append(f"{report.stretch_count} stretch opportunities identified.")

        if report.recurring_missing_skills:
            top = report.recurring_missing_skills[0][0]
            parts.append(f"Most common gap: '{top}'.")

        if report.strongest_job_direction:
            parts.append(
                f"Strongest opportunity direction: {report.strongest_job_direction}."
            )

        return " ".join(parts)
