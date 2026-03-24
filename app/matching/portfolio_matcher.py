"""
portfolio_matcher.py — Portfolio project matching against job requirements.

Maps candidate's portfolio projects to job requirements and recommends
which projects to highlight, order, and emphasize.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectMatch:
    """Scoring result for a single portfolio project against a job."""
    project_name: str
    match_score: float             # 0.0 – 10.0
    matched_technologies: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    relevance_reason: str = ""
    highlight_order: int = 0       # 1 = most relevant

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "match_score": self.match_score,
            "matched_technologies": self.matched_technologies,
            "matched_keywords": self.matched_keywords,
            "relevance_reason": self.relevance_reason,
            "highlight_order": self.highlight_order,
        }


@dataclass
class PortfolioMatchReport:
    """Full portfolio matching report for a job."""
    job_title: str = ""
    project_matches: list[ProjectMatch] = field(default_factory=list)
    top_project: str = ""
    recommendation: str = ""
    emphasis_advice: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_title": self.job_title,
            "project_matches": [p.to_dict() for p in self.project_matches],
            "top_project": self.top_project,
            "recommendation": self.recommendation,
            "emphasis_advice": self.emphasis_advice,
        }


# ── Role-type → emphasis keywords ────────────────────────────────────────────

_ROLE_EMPHASIS: dict[str, list[str]] = {
    "llm": ["llm", "rag", "langchain", "embeddings", "openai", "chatbot", "prompt"],
    "mlops": ["mlops", "pipeline", "deployment", "monitoring", "mlflow", "sagemaker"],
    "ai engineer": ["ai", "ml", "model", "training", "inference", "pytorch", "tensorflow"],
    "backend": ["api", "fastapi", "django", "flask", "rest", "database", "sql"],
    "platform": ["kubernetes", "terraform", "aws", "infrastructure", "docker", "ci/cd"],
    "data": ["data pipeline", "spark", "kafka", "airflow", "etl", "sql", "warehouse"],
}


def _job_text(job: Any) -> str:
    return f"{getattr(job, 'title', '')} {getattr(job, 'description', '')}".lower()


def _detect_role_type(text: str) -> str:
    """Detect the primary role type from job text."""
    best = ""
    best_hits = 0
    for role_type, keywords in _ROLE_EMPHASIS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_hits = hits
            best = role_type
    return best


def _score_project(
    project: dict[str, Any],
    job_text: str,
    role_type: str,
) -> ProjectMatch:
    """Score a single project against a job."""
    name = project.get("name", "Unnamed")
    description = (project.get("description") or "").lower()
    technologies = [t.lower() for t in project.get("technologies", [])]

    # Tech overlap
    matched_techs = [t for t in technologies if t in job_text]

    # Keyword overlap from description
    desc_words = [w for w in description.split() if len(w) > 3]
    matched_kws = [w for w in desc_words if w in job_text][:5]

    # Role-type alignment bonus
    role_keywords = _ROLE_EMPHASIS.get(role_type, [])
    role_hits = sum(1 for kw in role_keywords if kw in description or any(kw in t for t in technologies))

    # Score
    tech_ratio = len(matched_techs) / max(len(technologies), 1)
    base_score = tech_ratio * 8.0
    role_bonus = min(2.0, role_hits * 0.5)
    kw_bonus = min(1.0, len(matched_kws) * 0.2)

    final_score = round(min(10.0, base_score + role_bonus + kw_bonus), 2)

    reason = _build_reason(name, matched_techs, matched_kws, role_hits, role_type)

    return ProjectMatch(
        project_name=name,
        match_score=final_score,
        matched_technologies=matched_techs,
        matched_keywords=matched_kws[:3],
        relevance_reason=reason,
    )


def _build_reason(
    name: str,
    matched_techs: list[str],
    matched_kws: list[str],
    role_hits: int,
    role_type: str,
) -> str:
    parts = []
    if matched_techs:
        parts.append(f"uses {', '.join(matched_techs[:3])}")
    if role_hits >= 2:
        parts.append(f"strongly aligns with {role_type} requirements")
    elif role_hits == 1:
        parts.append(f"partially aligns with {role_type} work")
    if not parts:
        return "Limited overlap with job requirements."
    return f"{name} {' and '.join(parts)}."


class PortfolioMatcher:
    """
    Matches portfolio projects against job requirements.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}
        self._projects: list[dict[str, Any]] = self._profile.get("projects", [])

    def match(self, job: Any) -> PortfolioMatchReport:
        """Match portfolio projects against a job."""
        text = _job_text(job)
        job_title = getattr(job, "title", "")
        role_type = _detect_role_type(text)

        if not self._projects:
            return PortfolioMatchReport(
                job_title=job_title,
                recommendation="No portfolio projects available in profile.",
            )

        # Score each project
        matches = [_score_project(p, text, role_type) for p in self._projects]

        # Sort by score descending
        matches.sort(key=lambda x: x.match_score, reverse=True)

        # Assign highlight order
        for i, match in enumerate(matches):
            match.highlight_order = i + 1

        top = matches[0] if matches else None
        recommendation = _build_recommendation(top, role_type)
        emphasis = _build_emphasis_advice(matches, role_type)

        return PortfolioMatchReport(
            job_title=job_title,
            project_matches=matches,
            top_project=top.project_name if top else "",
            recommendation=recommendation,
            emphasis_advice=emphasis,
        )

    def best_project_for_job(self, job: Any) -> str:
        """Quick helper — returns just the top project name."""
        report = self.match(job)
        return report.top_project


def _build_recommendation(top_match: ProjectMatch | None, role_type: str) -> str:
    if not top_match:
        return "No matching projects found."
    if top_match.match_score >= 7.0:
        return (
            f"Lead with '{top_match.project_name}' — "
            f"strong match for this {role_type} role ({top_match.match_score:.1f}/10)."
        )
    if top_match.match_score >= 4.0:
        return (
            f"Use '{top_match.project_name}' as supporting evidence, "
            f"but explain how it relates to {role_type} work."
        )
    return (
        "No strong portfolio match found. "
        "Consider building a quick demo project targeting this role type."
    )


def _build_emphasis_advice(
    matches: list[ProjectMatch],
    role_type: str,
) -> list[str]:
    advice = []
    if matches:
        top = matches[0]
        advice.append(f"Place '{top.project_name}' first in your portfolio section.")
        if top.matched_technologies:
            advice.append(
                f"Emphasize {', '.join(top.matched_technologies[:3])} usage in description."
            )
    if len(matches) >= 2:
        second = matches[1]
        advice.append(f"Use '{second.project_name}' as a secondary example.")
    if len(matches) >= 3:
        weakest = matches[-1]
        if weakest.match_score < 3.0:
            advice.append(
                f"'{weakest.project_name}' has low relevance — "
                f"consider omitting or briefly mentioning it."
            )
    return advice
