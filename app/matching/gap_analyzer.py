"""
gap_analyzer.py — Per-job gap analysis engine.

Identifies what the candidate has, what is missing, how hard each gap is
to close, and provides a structured gap report.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Skill difficulty tiers ────────────────────────────────────────────────────
# Skills grouped by how long they typically take to learn for an experienced dev.

_EASY_SKILLS = {
    # Frameworks and tools learnable in days-weeks
    "fastapi", "flask", "pydantic", "sqlalchemy", "alembic",
    "pytest", "httpx", "celery", "redis",
    "langchain", "llama-index", "chromadb",
    "huggingface", "openai", "anthropic",
    "docker", "docker compose",
    "git", "github actions", "gitlab ci",
    "streamlit", "gradio",
    "pandas", "numpy", "matplotlib",
    "yaml", "json", "rest", "graphql",
}

_MEDIUM_SKILLS = {
    # Skills learnable in weeks-months
    "kubernetes", "k8s", "helm", "terraform", "ansible",
    "aws", "gcp", "azure", "cloud",
    "postgresql", "mysql", "mongodb", "elasticsearch",
    "kafka", "spark", "airflow", "dbt",
    "mlflow", "kubeflow", "sagemaker",
    "pytorch", "tensorflow",
    "typescript", "nodejs",
    "golang", "go",
    "ci/cd", "devops",
}

_HARD_SKILLS = {
    # Skills requiring months-years of dedicated learning
    "rust", "c++", "scala",
    "distributed systems", "system design",
    "reinforcement learning", "computer vision",
    "compilers", "operating systems",
    "cryptography", "security research",
    "java", "spring boot",
    "hadoop", "hive",
}


def _classify_skill_difficulty(skill: str) -> str:
    """Return 'easy', 'medium', or 'hard' for a given skill."""
    sk = skill.lower()
    if sk in _EASY_SKILLS:
        return "easy"
    if sk in _MEDIUM_SKILLS:
        return "medium"
    if sk in _HARD_SKILLS:
        return "hard"
    # Default: medium for unknown skills
    return "medium"


@dataclass
class GapItem:
    """A single identified gap."""
    skill: str
    difficulty: str          # easy | medium | hard
    is_willing_to_learn: bool = False
    close_strategy: str = ""


@dataclass
class GapReport:
    """Structured gap analysis report for a single job."""
    # What the candidate already has
    matched_skills: list[str] = field(default_factory=list)

    # What is missing
    all_gaps: list[GapItem] = field(default_factory=list)

    # Categorized
    easy_gaps: list[str] = field(default_factory=list)
    medium_gaps: list[str] = field(default_factory=list)
    hard_gaps: list[str] = field(default_factory=list)

    # Summary
    gap_count: int = 0
    gap_severity: str = "low"       # low | medium | high
    closeable: bool = True          # Whether gaps are realistically closeable
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_skills": self.matched_skills,
            "easy_gaps": self.easy_gaps,
            "medium_gaps": self.medium_gaps,
            "hard_gaps": self.hard_gaps,
            "gap_count": self.gap_count,
            "gap_severity": self.gap_severity,
            "closeable": self.closeable,
            "summary": self.summary,
        }


# ── Broad skill vocabulary for extraction ─────────────────────────────────────

_SKILL_VOCAB = [
    "python", "javascript", "typescript", "java", "go", "golang", "rust",
    "c++", "scala", "r", "sql", "nosql",
    "fastapi", "django", "flask", "pydantic", "sqlalchemy",
    "nodejs", "express", "spring",
    "react", "vue", "angular",
    "aws", "gcp", "azure", "cloud",
    "docker", "kubernetes", "k8s", "terraform", "helm", "ansible",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "kafka", "spark", "airflow", "dbt", "snowflake",
    "pytorch", "tensorflow", "sklearn", "scikit-learn", "pandas", "numpy",
    "mlflow", "kubeflow", "sagemaker", "mlops",
    "langchain", "openai", "anthropic", "huggingface", "embeddings",
    "rag", "llm", "gpt", "bert", "transformer",
    "ci/cd", "git", "github", "gitlab", "jenkins",
    "linux", "bash", "shell",
    "rest", "graphql", "grpc", "api",
    "machine learning", "deep learning", "nlp", "computer vision",
    "distributed systems", "microservices",
    "chromadb", "pinecone", "weaviate",
    "streamlit", "gradio",
    "pytest", "celery",
]


def _extract_job_skills(text: str) -> list[str]:
    """Extract likely required skills from job text."""
    return [sk for sk in _SKILL_VOCAB if sk in text.lower()]


class GapAnalyzer:
    """
    Analyzes the gap between a candidate profile and a job's requirements.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}
        # Build candidate skill set (lowercase)
        all_skills = self._profile.get("all_skills", [])
        preferred_techs = self._profile.get("preferred_technologies", [])
        positive_kws = self._profile.get("positive_keywords", [])
        willingness = self._profile.get("willingness_to_learn", [])

        self._candidate_skills = set(
            s.lower() for s in (all_skills + preferred_techs + positive_kws)
        )
        self._willing_lower = set(w.lower() for w in willingness)

    def analyze(self, job: Any) -> GapReport:
        """Analyze gap between candidate profile and a job."""
        text = f"{getattr(job, 'title', '')} {getattr(job, 'description', '')}".lower()

        job_skills = _extract_job_skills(text)
        if not job_skills:
            return GapReport(
                summary="No specific skills detected in job posting.",
                gap_severity="low",
                closeable=True,
            )

        # Categorize each job skill
        matched = []
        gap_items = []

        for sk in job_skills:
            if self._is_candidate_skill(sk):
                matched.append(sk)
            else:
                difficulty = _classify_skill_difficulty(sk)
                is_willing = any(sk in w or w in sk for w in self._willing_lower)
                strategy = self._close_strategy(sk, difficulty, is_willing)
                gap_items.append(GapItem(
                    skill=sk,
                    difficulty=difficulty,
                    is_willing_to_learn=is_willing,
                    close_strategy=strategy,
                ))

        easy = [g.skill for g in gap_items if g.difficulty == "easy"]
        medium = [g.skill for g in gap_items if g.difficulty == "medium"]
        hard = [g.skill for g in gap_items if g.difficulty == "hard"]

        gap_count = len(gap_items)
        severity = self._compute_severity(easy, medium, hard)
        closeable = len(hard) <= 1

        summary = self._build_summary(matched, easy, medium, hard)

        return GapReport(
            matched_skills=matched,
            all_gaps=gap_items,
            easy_gaps=easy,
            medium_gaps=medium,
            hard_gaps=hard,
            gap_count=gap_count,
            gap_severity=severity,
            closeable=closeable,
            summary=summary,
        )

    def _is_candidate_skill(self, skill: str) -> bool:
        """Check if a skill is in the candidate's repertoire."""
        for cs in self._candidate_skills:
            if skill == cs or skill in cs or cs in skill:
                return True
        return False

    def _compute_severity(
        self, easy: list[str], medium: list[str], hard: list[str]
    ) -> str:
        if not easy and not medium and not hard:
            return "low"
        if hard:
            return "high" if len(hard) >= 2 else "medium"
        if len(medium) >= 4:
            return "medium"
        return "low"

    def _close_strategy(self, skill: str, difficulty: str, is_willing: bool) -> str:
        if difficulty == "easy":
            return f"Learn {skill} basics through documentation / small project (1-2 weeks)."
        if difficulty == "medium":
            if is_willing:
                return f"Build a demo project using {skill} (2-4 weeks)."
            return f"Add {skill} to learning roadmap — 1-2 months to get comfortable."
        # hard
        return f"{skill} requires significant investment — evaluate if it's worth it for your track."

    def _build_summary(
        self,
        matched: list[str],
        easy: list[str],
        medium: list[str],
        hard: list[str],
    ) -> str:
        parts = []
        if matched:
            parts.append(f"You have: {', '.join(matched[:5])}.")
        if easy:
            parts.append(f"Easy to close: {', '.join(easy[:3])}.")
        if medium:
            parts.append(f"Medium effort needed: {', '.join(medium[:3])}.")
        if hard:
            parts.append(f"Hard gaps: {', '.join(hard[:2])} — significant investment required.")
        if not parts:
            return "Full skill match — no gaps identified."
        return " ".join(parts)
