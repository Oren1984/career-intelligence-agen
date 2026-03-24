"""
career_direction.py — Career track classification and direction analysis.

Classifies jobs into career tracks (AI Engineer, MLOps, DevOps+AI, etc.)
and evaluates whether a job supports or distracts from the candidate's
intended direction.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Career Track Definitions ──────────────────────────────────────────────────

TRACK_AI_ENGINEER = "Applied AI / LLM Engineer"
TRACK_MLOPS = "MLOps / ML Platform"
TRACK_DEVOPS_AI = "DevOps with AI Orientation"
TRACK_DATA_ENGINEER = "Data Engineer"
TRACK_BACKEND = "Backend / API Engineer"
TRACK_PLATFORM = "Platform / Infrastructure Engineer"
TRACK_DATA_SCIENTIST = "Data Scientist / Analyst"
TRACK_OTHER = "Other / Undefined"

ALL_TRACKS = [
    TRACK_AI_ENGINEER,
    TRACK_MLOPS,
    TRACK_DEVOPS_AI,
    TRACK_DATA_ENGINEER,
    TRACK_BACKEND,
    TRACK_PLATFORM,
    TRACK_DATA_SCIENTIST,
    TRACK_OTHER,
]

_TRACK_KEYWORDS: dict[str, list[str]] = {
    TRACK_AI_ENGINEER: [
        "llm", "large language model", "rag", "retrieval augmented",
        "langchain", "openai", "anthropic", "gpt", "claude",
        "prompt engineering", "embeddings", "fine-tuning",
        "ai engineer", "ai application", "llm application",
        "generative ai", "genai", "chatbot", "conversational ai",
        "vector database", "chromadb", "pinecone",
    ],
    TRACK_MLOPS: [
        "mlops", "ml platform", "model serving", "model deployment",
        "feature store", "mlflow", "kubeflow", "model monitoring",
        "ml pipeline", "experiment tracking", "model registry",
        "sagemaker", "vertex ai", "bentoml", "seldon",
        "machine learning engineer", "ml engineer",
    ],
    TRACK_DEVOPS_AI: [
        "devops", "site reliability", "sre", "platform engineering",
        "kubernetes", "terraform", "helm", "ci/cd", "infrastructure as code",
        "docker", "containerization", "cloud native",
        "aws", "gcp", "azure", "cloud infrastructure",
        "monitoring", "observability", "prometheus", "grafana",
    ],
    TRACK_DATA_ENGINEER: [
        "data engineer", "data pipeline", "etl", "elt",
        "spark", "kafka", "airflow", "dbt", "databricks",
        "snowflake", "bigquery", "data warehouse", "data lake",
        "streaming", "batch processing", "data orchestration",
    ],
    TRACK_BACKEND: [
        "backend", "api development", "rest api", "graphql",
        "microservices", "fastapi", "django", "flask", "nodejs",
        "java", "spring", "golang", "service architecture",
        "database design", "postgresql", "mysql",
    ],
    TRACK_PLATFORM: [
        "platform engineer", "developer platform", "internal tooling",
        "infrastructure engineer", "cloud engineer", "systems engineer",
        "reliability engineering", "network infrastructure",
    ],
    TRACK_DATA_SCIENTIST: [
        "data scientist", "data science", "machine learning", "statistical",
        "a/b testing", "experimentation", "analytics", "business intelligence",
        "jupyter", "r language", "statistics", "regression", "classification",
        "pandas", "sklearn", "scikit-learn", "matplotlib",
    ],
}

# ── Direction Analysis ────────────────────────────────────────────────────────

DIRECTION_ALIGNED = "aligned"
DIRECTION_PARTIAL = "partial"
DIRECTION_TRANSITION = "transition"     # Good stepping stone toward target
DIRECTION_OFF_TRACK = "off-track"
DIRECTION_UNKNOWN = "unknown"


@dataclass
class CareerDirectionResult:
    """Career direction analysis for a single job."""
    detected_track: str = TRACK_OTHER
    track_confidence: float = 0.0       # 0.0 – 1.0
    track_scores: dict[str, float] = field(default_factory=dict)

    direction_assessment: str = DIRECTION_UNKNOWN
    direction_explanation: str = ""

    supports_primary_goal: bool = False
    is_transition_role: bool = False
    is_distraction: bool = False

    advice: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_track": self.detected_track,
            "track_confidence": self.track_confidence,
            "track_scores": self.track_scores,
            "direction_assessment": self.direction_assessment,
            "direction_explanation": self.direction_explanation,
            "supports_primary_goal": self.supports_primary_goal,
            "is_transition_role": self.is_transition_role,
            "is_distraction": self.is_distraction,
            "advice": self.advice,
        }


class CareerDirectionAnalyzer:
    """
    Classifies jobs into career tracks and evaluates alignment with
    the candidate's intended career direction.
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        self._profile = profile or {}

        career_tracks = self._profile.get("career_tracks", {}) or {}
        self._primary_track = career_tracks.get("primary", "")
        self._acceptable_tracks = [t.lower() for t in career_tracks.get("acceptable", [])]
        self._avoided_tracks = [t.lower() for t in career_tracks.get("avoid", [])]
        self._preferred_domains = [d.lower() for d in self._profile.get("preferred_domains", [])]

    def analyze(self, job: Any) -> CareerDirectionResult:
        """Analyze career direction alignment for a job."""
        text = f"{getattr(job, 'title', '')} {getattr(job, 'description', '')}".lower()

        # Score each track
        track_scores = {}
        for track, keywords in _TRACK_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text)
            track_scores[track] = round(hits / max(len(keywords), 1), 3)

        # Find best track
        best_track = max(track_scores, key=track_scores.get)  # type: ignore[arg-type]
        best_score = track_scores[best_track]

        if best_score < 0.02:
            best_track = TRACK_OTHER
            confidence = 0.0
        else:
            confidence = min(1.0, best_score * 10)

        result = CareerDirectionResult(
            detected_track=best_track,
            track_confidence=round(confidence, 2),
            track_scores={k: v for k, v in sorted(
                track_scores.items(), key=lambda x: x[1], reverse=True
            )[:5]},
        )

        # ── Evaluate alignment with candidate's goals ─────────────────────
        result = self._evaluate_alignment(result, best_track, text)

        return result

    def _evaluate_alignment(
        self,
        result: CareerDirectionResult,
        detected_track: str,
        text: str,
    ) -> CareerDirectionResult:
        """Evaluate how well the detected track aligns with the candidate's direction."""
        primary_lower = self._primary_track.lower()
        detected_lower = detected_track.lower()

        # Check if avoided
        for avoided in self._avoided_tracks:
            if avoided in detected_lower or any(w in text for w in avoided.split()):
                result.direction_assessment = DIRECTION_OFF_TRACK
                result.is_distraction = True
                result.direction_explanation = (
                    f"This role appears to be '{detected_track}', "
                    f"which you have marked as a track to avoid."
                )
                result.advice = "Skip this role — it conflicts with your stated career direction."
                return result

        # Check primary alignment
        if primary_lower and (
            primary_lower in detected_lower
            or detected_lower in primary_lower
            or any(w in detected_lower for w in primary_lower.split("/"))
        ):
            result.direction_assessment = DIRECTION_ALIGNED
            result.supports_primary_goal = True
            result.direction_explanation = (
                f"This role matches your primary track: '{self._primary_track}'."
            )
            result.advice = "This role directly supports your career direction. Prioritize it."
            return result

        # Check acceptable tracks
        for acceptable in self._acceptable_tracks:
            if acceptable.lower() in detected_lower or detected_lower in acceptable.lower():
                result.direction_assessment = DIRECTION_PARTIAL
                result.supports_primary_goal = False
                result.direction_explanation = (
                    f"This role is in '{detected_track}', "
                    f"which is an acceptable (non-primary) track for you."
                )
                result.advice = "Acceptable role — good experience but not your primary direction."
                return result

        # Check if it could serve as a transition
        if _is_transition_role(detected_track, primary_lower):
            result.direction_assessment = DIRECTION_TRANSITION
            result.is_transition_role = True
            result.direction_explanation = (
                f"'{detected_track}' can serve as a stepping stone toward '{self._primary_track}'."
            )
            result.advice = (
                "Consider this if you need to build specific skills — "
                "keep your primary target in sight."
            )
            return result

        # Default: off-track
        result.direction_assessment = DIRECTION_OFF_TRACK
        result.is_distraction = True
        result.direction_explanation = (
            f"'{detected_track}' is not aligned with your target track or acceptable alternatives."
        )
        result.advice = (
            "Low strategic value for your career direction. "
            "Only consider if other factors are compelling."
        )
        return result


def _is_transition_role(detected_track: str, primary_lower: str) -> bool:
    """Check if a track is a reasonable stepping stone toward the primary."""
    transition_paths = {
        "mlops / ml platform": ["applied ai", "llm engineer", "ai engineer"],
        "devops with ai orientation": ["mlops", "platform", "applied ai"],
        "backend / api engineer": ["applied ai", "ai engineer", "mlops"],
        "platform / infrastructure engineer": ["mlops", "devops", "applied ai"],
    }
    for track_key, targets in transition_paths.items():
        if track_key in detected_track.lower():
            if any(t in primary_lower for t in targets):
                return True
    return False
