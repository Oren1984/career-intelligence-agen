"""
manual_job_analysis.py — Paste & Analyze pipeline for external job descriptions.

Accepts raw text (optionally with title / company / location overrides),
normalises it into a lightweight job object, and runs the full career
decision pipeline (CareerScorer, GapAnalyzer, ActionPlanner,
PortfolioMatcher, CareerDirectionAnalyzer).

No database writes.  Everything happens in-memory.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Lightweight job stand-in ──────────────────────────────────────────────────
# All existing scoring modules expect an object with .title and .description.
# ParsedJob satisfies that contract without touching the ORM.

@dataclass
class ParsedJob:
    """Normalised representation of a pasted job description."""
    title: str
    company: str
    location: str
    description: str                        # full raw text

    # Fields extracted by the parser (display only — scorers use title+description)
    extracted_skills: list[str] = field(default_factory=list)
    extracted_technologies: list[str] = field(default_factory=list)
    detected_seniority_hint: str = "unknown"


# ── Analysis result ───────────────────────────────────────────────────────────

@dataclass
class ManualAnalysisResult:
    """Aggregated output from all pipeline modules for a pasted job."""

    parsed_job: ParsedJob

    # CareerScorer output
    overall_fit_score: float = 0.0
    recommendation_label: str = ""
    recommendation_reason: str = ""
    score_breakdown: dict[str, float] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    gap_severity: str = "unknown"
    easy_to_close_gaps: list[str] = field(default_factory=list)
    hard_to_close_gaps: list[str] = field(default_factory=list)
    career_direction_alignment: str = "unknown"

    # Should I Apply? decision
    apply_decision: str = "CONDITIONAL"     # YES | NO | CONDITIONAL
    apply_explanation: str = ""

    # ActionPlanner output
    action_items: list[str] = field(default_factory=list)

    # PortfolioMatcher output
    best_matching_project: str = ""
    portfolio_recommendation: str = ""
    portfolio_highlights: list[str] = field(default_factory=list)

    # CareerDirectionAnalyzer output
    detected_track: str = ""
    direction_assessment: str = ""
    direction_explanation: str = ""
    direction_advice: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "parsed_title": self.parsed_job.title,
            "parsed_company": self.parsed_job.company,
            "parsed_location": self.parsed_job.location,
            "extracted_skills": self.parsed_job.extracted_skills,
            "overall_fit_score": self.overall_fit_score,
            "recommendation_label": self.recommendation_label,
            "recommendation_reason": self.recommendation_reason,
            "score_breakdown": self.score_breakdown,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "risks": self.risks,
            "gap_severity": self.gap_severity,
            "easy_to_close_gaps": self.easy_to_close_gaps,
            "hard_to_close_gaps": self.hard_to_close_gaps,
            "career_direction_alignment": self.career_direction_alignment,
            "apply_decision": self.apply_decision,
            "apply_explanation": self.apply_explanation,
            "action_items": self.action_items,
            "best_matching_project": self.best_matching_project,
            "portfolio_recommendation": self.portfolio_recommendation,
            "portfolio_highlights": self.portfolio_highlights,
            "detected_track": self.detected_track,
            "direction_assessment": self.direction_assessment,
            "direction_explanation": self.direction_explanation,
            "direction_advice": self.direction_advice,
        }


# ── Technology / skill vocabulary (shared with career_scorer) ─────────────────

_TECH_VOCAB: list[str] = [
    "python", "javascript", "typescript", "java", "go", "golang", "rust",
    "c++", "scala", "sql", "nosql",
    "fastapi", "django", "flask", "pydantic", "sqlalchemy",
    "nodejs", "express", "spring",
    "react", "vue", "angular",
    "aws", "gcp", "azure",
    "docker", "kubernetes", "k8s", "terraform", "helm", "ansible",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "kafka", "spark", "airflow", "dbt", "snowflake",
    "pytorch", "tensorflow", "sklearn", "scikit-learn", "pandas", "numpy",
    "mlflow", "kubeflow", "sagemaker", "mlops",
    "langchain", "openai", "anthropic", "huggingface", "embeddings",
    "rag", "llm", "gpt", "bert", "transformer",
    "ci/cd", "git", "github", "gitlab",
    "linux", "bash",
    "rest", "graphql", "grpc",
    "machine learning", "deep learning", "nlp", "computer vision",
    "chromadb", "pinecone", "weaviate",
    "streamlit", "gradio",
    "pytest",
]

_SENIORITY_SENIOR = re.compile(
    r"\b(senior|lead|principal|staff|director|head\s+of|[7-9]\+\s*years?|10\+\s*years?)\b",
    re.IGNORECASE,
)
_SENIORITY_JUNIOR = re.compile(
    r"\b(junior|entry[\s-]level|graduate|intern|0[-–]2\s*years?|1[-–]2\s*years?)\b",
    re.IGNORECASE,
)
_SENIORITY_MID = re.compile(
    r"\b(mid[\s-]level|mid\b|[2-5]\+\s*years?|[2-5][-–][5-7]\s*years?)\b",
    re.IGNORECASE,
)


def _detect_seniority_hint(text: str) -> str:
    if _SENIORITY_SENIOR.search(text):
        return "senior"
    if _SENIORITY_JUNIOR.search(text):
        return "junior"
    if _SENIORITY_MID.search(text):
        return "mid"
    return "unknown"


def _extract_technologies(text: str) -> list[str]:
    """Return tech tokens found in text using word-boundary matching."""
    lower = text.lower()
    found = []
    for tech in _TECH_VOCAB:
        try:
            if re.search(r"\b" + re.escape(tech) + r"\b", lower):
                found.append(tech)
        except re.error:
            if tech in lower:
                found.append(tech)
    return found


def _infer_title_from_text(text: str) -> str:
    """
    Try to extract a job title from the first non-empty line of the text.
    Falls back to 'Job' when the first line looks too long to be a title.
    """
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) <= 80:
            return line
    return "Job"


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_job_text(
    raw_text: str,
    title: str = "",
    company: str = "",
    location: str = "",
) -> ParsedJob:
    """
    Normalise a pasted job description into a ParsedJob.

    Args:
        raw_text:  Full job description text pasted by the user.
        title:     Optional override; inferred from first line if empty.
        company:   Optional; shown in output but does not affect scoring.
        location:  Optional; shown in output but does not affect scoring.

    Returns:
        ParsedJob ready to be passed to the scoring pipeline.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise ValueError("Job description text must not be empty.")

    resolved_title = title.strip() if title.strip() else _infer_title_from_text(raw_text)

    technologies = _extract_technologies(raw_text)
    seniority_hint = _detect_seniority_hint(raw_text)

    return ParsedJob(
        title=resolved_title,
        company=company.strip() or "Unknown Company",
        location=location.strip() or "Unknown Location",
        description=raw_text,
        extracted_skills=technologies,
        extracted_technologies=technologies,
        detected_seniority_hint=seniority_hint,
    )


# ── Should I Apply? decision ──────────────────────────────────────────────────

def _derive_apply_decision(
    score: float,
    label: str,
    gap_severity: str,
    hard_gaps: list[str],
) -> tuple[str, str]:
    """
    Return (decision, explanation) where decision is YES / NO / CONDITIONAL.
    """
    from app.matching.career_scorer import (
        LABEL_APPLY_NOW, LABEL_APPLY_AFTER_FIX,
        LABEL_NOT_WORTH_IT, LABEL_MARKET_SIGNAL,
        LABEL_WRONG_TIMING,
    )

    if label == LABEL_APPLY_NOW:
        return "YES", "Strong fit across all dimensions. Apply promptly."

    if label == LABEL_APPLY_AFTER_FIX:
        easy_msg = f" Address: {', '.join(hard_gaps[:2])}." if hard_gaps else ""
        return "YES", f"Good fit with minor gaps.{easy_msg} Apply after a quick tailoring."

    if label in (LABEL_NOT_WORTH_IT,):
        return "NO", "Too many mismatches. Focus your time on better-aligned roles."

    if label == LABEL_MARKET_SIGNAL:
        return "NO", "Role is off your target track. Treat as a market signal only."

    if label == LABEL_WRONG_TIMING:
        return "CONDITIONAL", (
            "The role is interesting but the seniority bar is too high right now. "
            "Apply only if you have strong evidence for the level."
        )

    if score >= 60 and gap_severity in ("low", "medium") and len(hard_gaps) <= 1:
        return "CONDITIONAL", "Decent fit. Worth applying if you can address the highlighted gaps."

    if score < 45:
        return "NO", "Score is too low. Better to focus on stronger matches first."

    return "CONDITIONAL", (
        "Moderate fit. Apply if the role excites you, but manage your expectations."
    )


# ── Main pipeline ─────────────────────────────────────────────────────────────

class ManualJobAnalyzer:
    """
    Runs the full career decision pipeline on a pasted job description.

    Instantiate once per session with the candidate profile; reuse for
    multiple analyses without reload cost.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}
        # Lazy-instantiate scorers to avoid import cost at module load
        self._career_scorer = None
        self._gap_analyzer = None
        self._action_planner = None
        self._portfolio_matcher = None
        self._direction_analyzer = None

    def _get_career_scorer(self):
        if self._career_scorer is None:
            from app.matching.career_scorer import CareerScorer
            self._career_scorer = CareerScorer(profile=self._profile)
        return self._career_scorer

    def _get_gap_analyzer(self):
        if self._gap_analyzer is None:
            from app.matching.gap_analyzer import GapAnalyzer
            self._gap_analyzer = GapAnalyzer(profile=self._profile)
        return self._gap_analyzer

    def _get_action_planner(self):
        if self._action_planner is None:
            from app.matching.action_planner import ActionPlanner
            self._action_planner = ActionPlanner(profile=self._profile)
        return self._action_planner

    def _get_portfolio_matcher(self):
        if self._portfolio_matcher is None:
            from app.matching.portfolio_matcher import PortfolioMatcher
            self._portfolio_matcher = PortfolioMatcher(profile=self._profile)
        return self._portfolio_matcher

    def _get_direction_analyzer(self):
        if self._direction_analyzer is None:
            from app.matching.career_direction import CareerDirectionAnalyzer
            self._direction_analyzer = CareerDirectionAnalyzer(profile=self._profile)
        return self._direction_analyzer

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> ManualAnalysisResult:
        """
        Full pipeline: parse → score → gap → action → portfolio → direction.

        Args:
            raw_text:  Job description text pasted by the user.
            title:     Optional job title override.
            company:   Optional company name override.
            location:  Optional location override.

        Returns:
            ManualAnalysisResult with all sections populated.
        """
        parsed = parse_job_text(raw_text, title=title, company=company, location=location)
        result = ManualAnalysisResult(parsed_job=parsed)

        # ── CareerScorer ──────────────────────────────────────────────────────
        try:
            cs = self._get_career_scorer().score(parsed)
            result.overall_fit_score = cs.overall_fit_score
            result.recommendation_label = cs.recommendation_label
            result.recommendation_reason = cs.recommendation_reason
            result.score_breakdown = cs.score_breakdown
            result.strengths = cs.strengths
            result.gaps = cs.gaps
            result.risks = cs.risks
            result.gap_severity = cs.gap_severity
            result.easy_to_close_gaps = cs.easy_to_close_gaps
            result.hard_to_close_gaps = cs.hard_to_close_gaps
            result.career_direction_alignment = cs.career_direction_alignment
        except Exception as exc:
            logger.error("CareerScorer failed: %s", exc)
            result.recommendation_label = "Analysis Error"

        # ── Should I Apply? ───────────────────────────────────────────────────
        result.apply_decision, result.apply_explanation = _derive_apply_decision(
            score=result.overall_fit_score,
            label=result.recommendation_label,
            gap_severity=result.gap_severity,
            hard_gaps=result.hard_to_close_gaps,
        )

        # ── ActionPlanner ─────────────────────────────────────────────────────
        try:
            plan = self._get_action_planner().plan(parsed, career_score_result=cs)
            # Flatten to a concise ordered list for display
            all_actions = plan.high_priority + plan.medium_priority + plan.low_priority
            result.action_items = [a.action for a in all_actions[:5]]
        except Exception as exc:
            logger.error("ActionPlanner failed: %s", exc)

        # ── PortfolioMatcher ──────────────────────────────────────────────────
        try:
            pm = self._get_portfolio_matcher().match(parsed)
            result.best_matching_project = pm.top_project
            result.portfolio_recommendation = pm.recommendation
            result.portfolio_highlights = pm.emphasis_advice
        except Exception as exc:
            logger.error("PortfolioMatcher failed: %s", exc)

        # ── CareerDirectionAnalyzer ───────────────────────────────────────────
        try:
            da = self._get_direction_analyzer().analyze(parsed)
            result.detected_track = da.detected_track
            result.direction_assessment = da.direction_assessment
            result.direction_explanation = da.direction_explanation
            result.direction_advice = da.advice
        except Exception as exc:
            logger.error("CareerDirectionAnalyzer failed: %s", exc)

        return result

    def analyze_apply_only(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """
        Focused output: Should I Apply?

        Runs the full pipeline internally but returns only the decision
        section plus top 2 action items.
        """
        result = self.analyze(raw_text, title=title, company=company, location=location)
        return {
            "apply_decision": result.apply_decision,
            "apply_explanation": result.apply_explanation,
            "recommendation_label": result.recommendation_label,
            "overall_fit_score": result.overall_fit_score,
            "top_actions": result.action_items[:2],
        }

    def analyze_portfolio_only(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """
        Focused output: Which project should I highlight?

        Runs only the PortfolioMatcher (fast path — skips career scoring).
        """
        parsed = parse_job_text(raw_text, title=title, company=company, location=location)
        try:
            pm = self._get_portfolio_matcher().match(parsed)
            return {
                "best_matching_project": pm.top_project,
                "recommendation": pm.recommendation,
                "emphasis_advice": pm.emphasis_advice,
                "all_matches": [m.to_dict() for m in pm.project_matches],
            }
        except Exception as exc:
            logger.error("PortfolioMatcher failed: %s", exc)
            return {
                "best_matching_project": "",
                "recommendation": f"Analysis failed: {exc}",
                "emphasis_advice": [],
                "all_matches": [],
            }
