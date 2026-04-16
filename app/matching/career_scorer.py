"""
career_scorer.py — Multi-factor career decision scorer.

Replaces the simple high/medium/low keyword approach with a structured,
explainable scoring system that evaluates each job across multiple dimensions
and produces a recommendation label.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Recommendation Labels ─────────────────────────────────────────────────────

LABEL_APPLY_NOW = "Apply Now"
LABEL_APPLY_AFTER_FIX = "Apply After Small Fix"
LABEL_STRETCH = "Stretch Opportunity"
LABEL_WRONG_TIMING = "Good Role, Wrong Timing"
LABEL_WRONG_ROLE = "Good Company, Wrong Role"
LABEL_NOT_WORTH_IT = "Not Worth It"
LABEL_MARKET_SIGNAL = "Market Signal Only"

ALL_LABELS = [
    LABEL_APPLY_NOW,
    LABEL_APPLY_AFTER_FIX,
    LABEL_STRETCH,
    LABEL_WRONG_TIMING,
    LABEL_WRONG_ROLE,
    LABEL_NOT_WORTH_IT,
    LABEL_MARKET_SIGNAL,
]

# ── Seniority Keywords ────────────────────────────────────────────────────────

_SENIOR_SIGNALS = [
    "senior", "lead", "principal", "staff", "director", "head of",
    "8+ years", "7+ years", "6+ years", "10+ years",
]
_JUNIOR_SIGNALS = [
    "junior", "entry level", "entry-level", "graduate", "intern",
    "0-2 years", "1-2 years", "1+ year",
]
_MID_SIGNALS = [
    "mid", "mid-level", "mid level", "3+ years", "2+ years", "4+ years",
    "2-5 years", "3-5 years",
]

# ── Work Mode Keywords ────────────────────────────────────────────────────────

_REMOTE_SIGNALS = ["remote", "work from home", "wfh", "fully remote", "distributed"]
_HYBRID_SIGNALS = ["hybrid", "flexible", "partially remote", "2 days", "3 days office"]
_ONSITE_SIGNALS = ["on-site", "onsite", "on site", "in office", "office only", "relocation"]

# ── Domain Keywords ───────────────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "AI/ML Engineering": [
        "machine learning", "deep learning", "neural network", "ai engineer",
        "ml engineer", "artificial intelligence", "computer vision", "nlp",
        "natural language processing",
    ],
    "LLM Applications": [
        "llm", "large language model", "gpt", "chatgpt", "claude", "rag",
        "retrieval augmented", "prompt engineering", "langchain", "embeddings",
        "vector database", "openai", "anthropic", "fine-tuning",
    ],
    "MLOps": [
        "mlops", "ml platform", "model serving", "feature store", "mlflow",
        "kubeflow", "model deployment", "model monitoring", "data pipeline",
        "experiment tracking",
    ],
    "Platform Engineering": [
        "platform engineer", "developer platform", "internal tooling",
        "infrastructure", "devops", "kubernetes", "terraform", "helm",
        "cloud native", "aws", "gcp", "azure",
    ],
    "Data Engineering": [
        "data engineer", "data pipeline", "etl", "spark", "kafka",
        "airflow", "dbt", "warehouse", "snowflake", "bigquery", "databricks",
    ],
    "Backend Engineering": [
        "backend", "api", "rest", "graphql", "microservices", "fastapi",
        "django", "flask", "nodejs", "java", "golang", "service",
    ],
}

# ── Score Weights ─────────────────────────────────────────────────────────────

_WEIGHTS = {
    "title_relevance": 0.20,
    "skill_overlap": 0.25,
    "seniority_realism": 0.15,
    "domain_alignment": 0.15,
    "work_mode_alignment": 0.10,
    "strategic_alignment": 0.10,
    "portfolio_alignment": 0.05,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"


# ── Result Dataclass ──────────────────────────────────────────────────────────

@dataclass
class CareerScoreResult:
    """Full career decision scoring result for a single job."""

    # Overall
    overall_fit_score: float = 0.0          # 0–100
    recommendation_label: str = LABEL_NOT_WORTH_IT
    recommendation_reason: str = ""

    # Breakdown (each 0–10)
    score_breakdown: dict[str, float] = field(default_factory=dict)

    # Explanation
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    # Gap metadata
    gap_severity: str = "low"               # low | medium | high
    easy_to_close_gaps: list[str] = field(default_factory=list)
    hard_to_close_gaps: list[str] = field(default_factory=list)

    # Career direction
    career_direction_alignment: str = "unknown"  # aligned | partial | off-track | unknown
    detected_domain: str = ""
    detected_seniority: str = "unknown"
    detected_work_mode: str = "unknown"

    # Portfolio
    best_matching_project: str = ""
    portfolio_highlights: list[str] = field(default_factory=list)

    # Action items
    action_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
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
            "detected_domain": self.detected_domain,
            "detected_seniority": self.detected_seniority,
            "detected_work_mode": self.detected_work_mode,
            "best_matching_project": self.best_matching_project,
            "portfolio_highlights": self.portfolio_highlights,
            "action_items": self.action_items,
        }


# ── Helper Functions ──────────────────────────────────────────────────────────

def _job_text(job: Any) -> str:
    title = getattr(job, "title", "") or ""
    desc = getattr(job, "description", "") or ""
    return f"{title} {desc}".lower()


def _detect_seniority(text: str) -> str:
    for sig in _SENIOR_SIGNALS:
        if sig in text:
            return "senior"
    for sig in _JUNIOR_SIGNALS:
        if sig in text:
            return "junior"
    for sig in _MID_SIGNALS:
        if sig in text:
            return "mid"
    return "unknown"


def _detect_work_mode(text: str) -> str:
    remote_hits = sum(1 for s in _REMOTE_SIGNALS if s in text)
    hybrid_hits = sum(1 for s in _HYBRID_SIGNALS if s in text)
    onsite_hits = sum(1 for s in _ONSITE_SIGNALS if s in text)

    if remote_hits >= hybrid_hits and remote_hits >= onsite_hits and remote_hits > 0:
        return "remote"
    if hybrid_hits >= onsite_hits and hybrid_hits > 0:
        return "hybrid"
    if onsite_hits > 0:
        return "onsite"
    return "unknown"


def _detect_domain(text: str) -> str:
    """Return the best-matching domain name."""
    best_domain = ""
    best_hits = 0
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_domain = domain
    return best_domain


def _extract_skill_tokens(text: str) -> list[str]:
    """
    Extract likely skill/tech tokens from job text using a broad skill vocabulary.
    Uses word-boundary matching to avoid false positives on partial substrings
    (e.g. "r" should not match inside "marketing").
    Returns lowercase tokens.
    """
    import re

    skill_vocab = [
        "python", "javascript", "typescript", "java", "go", "golang", "rust",
        "c++", "scala", "r", "sql", "nosql",
        "fastapi", "django", "flask", "nodejs", "express", "spring",
        "react", "vue", "angular",
        "aws", "gcp", "azure", "cloud",
        "docker", "kubernetes", "k8s", "terraform", "helm", "ansible",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "kafka", "spark", "airflow", "dbt", "snowflake",
        "pytorch", "tensorflow", "sklearn", "pandas", "numpy",
        "mlflow", "kubeflow", "sagemaker", "mlops",
        "langchain", "openai", "anthropic", "huggingface", "embeddings",
        "rag", "llm", "gpt", "bert", "transformer",
        "ci/cd", "git", "github", "gitlab", "jenkins",
        "linux", "bash", "shell",
        "rest", "graphql", "grpc", "api",
        "machine learning", "deep learning", "nlp", "computer vision",
    ]
    matched = []
    for sk in skill_vocab:
        # Use word boundaries for pure alpha tokens; substring match for special tokens
        try:
            if re.search(r"\b" + re.escape(sk) + r"\b", text):
                matched.append(sk)
        except re.error:
            if sk in text:
                matched.append(sk)
    return matched


def _score_title_relevance(text: str, profile_dict: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    """Score how well the job title matches target roles. Returns (score, strengths, gaps)."""
    title = text.split(" ")[0] if text else ""
    # Use first 5 words as title proxy
    title_words = " ".join(text.split()[:6])

    target_roles = [r.lower() for r in profile_dict.get("target_roles", [])]
    preferred_track = profile_dict.get("preferred_role_track", "").lower()

    strengths = []
    gaps = []
    score = 5.0  # neutral default

    # Exact role match
    for role in target_roles:
        role_words = role.split()
        if all(w in text for w in role_words):
            score = 10.0
            strengths.append(f"Title matches target role: {role}")
            return score, strengths, gaps

    # Partial role match
    for role in target_roles:
        role_words = role.split()
        matched = sum(1 for w in role_words if w in text)
        if matched / max(len(role_words), 1) >= 0.5:
            score = max(score, 7.0)
            strengths.append(f"Title partially matches: {role}")

    # Track keyword match
    if preferred_track and any(w in text for w in preferred_track.split()):
        score = max(score, 6.5)
        strengths.append(f"Title aligns with preferred track: {preferred_track}")

    # General AI/ML signals
    ai_signals = ["ai", "ml", "machine learning", "llm", "engineer", "platform"]
    ai_hits = sum(1 for s in ai_signals if s in title_words)
    if ai_hits >= 2:
        score = max(score, 6.0)

    if score < 5.5:
        gaps.append("Job title doesn't align with target roles")

    return round(score, 2), strengths, gaps


def _score_skill_overlap(text: str, profile_dict: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    """Score skill coverage. Returns (score, matched_skills, missing_skills)."""
    all_skills_lower = [s.lower() for s in profile_dict.get("all_skills", [])]
    preferred_techs = [t.lower() for t in profile_dict.get("preferred_technologies", [])]
    positive_kws = [kw.lower() for kw in profile_dict.get("positive_keywords", [])]
    # strong_skills are explicitly stated confident skills — always count them
    strong_skills = [s.lower() for s in profile_dict.get("strong_skills", [])]

    candidate_skills = list(set(all_skills_lower + preferred_techs + positive_kws + strong_skills))
    job_skills = _extract_skill_tokens(text)

    if not job_skills:
        return 5.0, [], []  # Can't evaluate, neutral

    matched = [sk for sk in job_skills if any(sk in cs or cs in sk for cs in candidate_skills)]
    missing = [sk for sk in job_skills if sk not in matched]

    overlap_ratio = len(matched) / max(len(job_skills), 1)
    score = round(overlap_ratio * 10.0, 2)

    return score, matched, missing


def _score_seniority_realism(
    text: str,
    detected_seniority: str,
    profile_dict: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    """Score seniority match. Returns (score, strengths, gaps)."""
    experience_level = profile_dict.get("experience_level", "mid").lower()
    strengths = []
    gaps = []

    if detected_seniority == "unknown":
        return 7.5, ["Seniority level not specified — assuming accessible"], []

    # Exact match
    if detected_seniority == experience_level:
        return 10.0, [f"Seniority match: {detected_seniority}"], []

    # Mid candidate → junior role: slight mismatch (overqualified)
    if experience_level == "mid" and detected_seniority == "junior":
        return 6.0, [], ["Role may be too junior for your experience level"]

    # Mid candidate → senior role: realistic stretch
    if experience_level == "mid" and detected_seniority == "senior":
        return 4.0, [], ["Senior role may require more experience than you currently have"]

    # Junior candidate → senior role: big mismatch
    if experience_level == "junior" and detected_seniority == "senior":
        return 2.0, [], ["Senior role is a significant mismatch for junior level"]

    return 5.0, [], [f"Seniority mismatch: role is {detected_seniority}, you are {experience_level}"]


def _score_domain_alignment(
    text: str,
    detected_domain: str,
    profile_dict: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    """Score domain match. Returns (score, strengths, gaps)."""
    preferred_domains = [d.lower() for d in profile_dict.get("preferred_domains", [])]
    strengths = []
    gaps = []

    if not detected_domain:
        return 5.0, [], ["Could not detect job domain"]

    detected_lower = detected_domain.lower()

    for pd in preferred_domains:
        if pd in detected_lower or detected_lower in pd:
            strengths.append(f"Domain match: {detected_domain}")
            return 10.0, strengths, gaps

    # Partial overlap check
    domain_words = set(detected_lower.split())
    for pd in preferred_domains:
        pd_words = set(pd.split("/"))
        if domain_words & pd_words:
            strengths.append(f"Partial domain match: {detected_domain}")
            return 7.0, strengths, gaps

    gaps.append(f"Domain '{detected_domain}' is not in preferred domains")
    return 3.0, strengths, gaps


def _score_work_mode_alignment(
    detected_work_mode: str,
    profile_dict: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    """Score work mode match. Returns (score, strengths, gaps)."""
    preference = profile_dict.get("work_mode_preference", "any").lower()

    if preference == "any" or detected_work_mode == "unknown":
        return 7.5, ["No specific work mode requirement"], []

    if preference == detected_work_mode:
        return 10.0, [f"Work mode match: {detected_work_mode}"], []

    # Hybrid is a partial match for both remote and onsite
    if detected_work_mode == "hybrid" and preference in ("remote", "onsite"):
        return 6.0, [], [f"Work mode is hybrid (preferred: {preference})"]

    if detected_work_mode == "onsite" and preference == "remote":
        return 2.0, [], ["Role is onsite but you prefer remote"]

    if detected_work_mode == "remote" and preference == "onsite":
        return 6.0, [], ["Role is remote but you prefer onsite"]

    return 5.0, [], [f"Work mode mismatch: {detected_work_mode} vs preference {preference}"]


def _score_strategic_alignment(
    text: str,
    profile_dict: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    """Score strategic career alignment. Returns (score, strengths, gaps)."""
    short_goal = (profile_dict.get("short_term_goal") or "").lower()
    long_goal = (profile_dict.get("long_term_goal") or "").lower()
    strengths = []
    gaps = []

    # Extract goal keywords (nouns/verbs > 3 chars)
    goal_text = f"{short_goal} {long_goal}"
    goal_tokens = [w for w in re.findall(r"[a-z]+", goal_text) if len(w) > 3]
    goal_tokens = list(set(goal_tokens))

    if not goal_tokens:
        return 6.0, [], []

    hits = sum(1 for tok in goal_tokens if tok in text)
    ratio = hits / min(len(goal_tokens), 10)  # cap at 10 goal tokens

    score = round(ratio * 10.0, 2)

    if score >= 7.0:
        strengths.append("Role aligns with your stated career goals")
    elif score >= 4.0:
        strengths.append("Role partially aligns with career goals")
    else:
        gaps.append("Role has limited alignment with stated career goals")

    return score, strengths, gaps


def _score_portfolio_alignment(
    text: str,
    projects: list[dict[str, Any]],
) -> tuple[float, str, list[str]]:
    """Score portfolio match. Returns (score, best_project_name, highlights)."""
    if not projects:
        return 5.0, "", []

    best_score = 0.0
    best_project = ""
    highlights = []

    for project in projects:
        techs = [t.lower() for t in project.get("technologies", [])]
        project_name = project.get("name", "Unnamed")
        proj_desc = project.get("description", "").lower()

        # Count tech matches
        tech_hits = sum(1 for t in techs if t in text)
        desc_hit = any(w in text for w in proj_desc.split() if len(w) > 4)

        proj_score = (tech_hits / max(len(techs), 1)) * 8.0
        if desc_hit:
            proj_score = min(10.0, proj_score + 1.0)

        if proj_score > best_score:
            best_score = proj_score
            best_project = project_name

        if tech_hits > 0:
            matched_techs = [t for t in techs if t in text]
            highlights.append(f"{project_name}: uses {', '.join(matched_techs[:3])}")

    return round(best_score, 2), best_project, highlights[:3]


def _compute_gap_severity(missing_skills: list[str], hard_gaps: list[str]) -> str:
    """Classify overall gap severity."""
    total_gaps = len(missing_skills) + len(hard_gaps)
    if total_gaps == 0:
        return "low"
    if total_gaps <= 2:
        return "low"
    if total_gaps <= 5:
        return "medium"
    return "high"


def _classify_easy_vs_hard_gaps(
    missing_skills: list[str],
    willingness_to_learn: list[str],
) -> tuple[list[str], list[str]]:
    """Split gaps into easy-to-close (willing to learn) vs hard."""
    willing_lower = [w.lower() for w in willingness_to_learn]
    easy = []
    hard = []
    for skill in missing_skills:
        if any(skill in w or w in skill for w in willing_lower):
            easy.append(skill)
        else:
            hard.append(skill)
    return easy, hard


def _assign_label(
    overall_score: float,
    gap_severity: str,
    seniority_score: float,
    work_mode_score: float,
    career_direction_alignment: str,
    hard_gaps: list[str],
) -> tuple[str, str]:
    """Assign recommendation label and reason."""

    # Very low fit — check early to avoid false positives
    if overall_score < 40:
        return LABEL_NOT_WORTH_IT, "Too many gaps or mismatches — not worth prioritizing."

    # Seniority mismatch check BEFORE apply labels (seniority is a hard blocker)
    if overall_score >= 55 and seniority_score < 4.0:
        return LABEL_WRONG_TIMING, "Good role but seniority level is a mismatch for now."

    # Work mode dealbreaker
    if work_mode_score <= 2.0 and overall_score >= 55:
        return LABEL_WRONG_ROLE, "Good role but work mode is incompatible with your preference."

    # Strong match → Apply Now
    if overall_score >= 75 and gap_severity == "low" and seniority_score >= 6.0:
        return LABEL_APPLY_NOW, "Strong overall fit with no major gaps."

    # Good match with fixable gaps → Apply After Small Fix
    if overall_score >= 60 and gap_severity in ("low", "medium") and len(hard_gaps) <= 1:
        return LABEL_APPLY_AFTER_FIX, "Good fit — address 1-2 skill gaps to strengthen your application."

    # Career direction misaligned but domain familiar
    if career_direction_alignment == "off-track" and overall_score >= 40:
        return LABEL_MARKET_SIGNAL, "Keep as market signal — not aligned with your target direction."

    # Off-track but interesting stretch
    if 45 <= overall_score < 60:
        return LABEL_STRETCH, "Stretch opportunity — achievable with focused effort."

    # Default stretch
    return LABEL_STRETCH, "Moderate fit — worth a stretch if you're interested in the domain."


def _build_action_items(
    label: str,
    easy_gaps: list[str],
    hard_gaps: list[str],
    best_project: str,
    seniority_score: float,
    work_mode_score: float,
) -> list[str]:
    """Generate practical next-step action items."""
    items = []

    if label == LABEL_APPLY_NOW:
        items.append("Apply within 24-48 hours — strong fit.")
        if best_project:
            items.append(f"Lead with '{best_project}' in your application.")

    elif label == LABEL_APPLY_AFTER_FIX:
        if easy_gaps:
            items.append(f"Quickly address: {', '.join(easy_gaps[:2])} (easy to show familiarity).")
        if best_project:
            items.append(f"Highlight '{best_project}' as proof of relevant work.")
        items.append("Tailor your CV summary to match the job description language.")

    elif label == LABEL_STRETCH:
        if hard_gaps:
            items.append(f"Build experience in: {', '.join(hard_gaps[:2])} before applying.")
        items.append("Do a side project that closes the gap, then re-evaluate.")
        items.append("Apply anyway if you feel confident — stretch roles drive growth.")

    elif label == LABEL_WRONG_TIMING:
        items.append("Bookmark for 6-12 months — wait until you have more seniority signals.")
        items.append("Use as a reference to understand what you need to grow into.")

    elif label == LABEL_MARKET_SIGNAL:
        items.append("Note recurring requirements as market signals for your learning roadmap.")
        items.append("Do not prioritize — focus on better-aligned opportunities first.")

    elif label == LABEL_NOT_WORTH_IT:
        items.append("Skip — too many mismatches.")

    return items


# ── Main Scorer Class ─────────────────────────────────────────────────────────

class CareerScorer:
    """
    Multi-factor career decision scorer.

    Evaluates a job against a candidate profile across 7 dimensions,
    produces an overall fit score (0-100), a recommendation label,
    and explainable outputs (strengths, gaps, risks, action items).
    """

    def __init__(self, profile: dict[str, Any] | None = None):
        """
        Args:
            profile: dict from CandidateProfile.to_dict() or raw profile dict.
                     If None, uses neutral defaults (all scores = 5.0).
        """
        self._profile = profile or {}

    def score(self, job: Any) -> CareerScoreResult:
        """Score a Job ORM object (or any object with .title and .description)."""
        text = _job_text(job)
        profile = self._profile
        result = CareerScoreResult()

        # ── Detect job metadata ────────────────────────────────────────────
        result.detected_seniority = _detect_seniority(text)
        result.detected_work_mode = _detect_work_mode(text)
        result.detected_domain = _detect_domain(text)

        # ── Score each dimension ───────────────────────────────────────────
        title_score, t_str, t_gap = _score_title_relevance(text, profile)
        skill_score, matched_skills, missing_skills = _score_skill_overlap(text, profile)
        seniority_score, s_str, s_gap = _score_seniority_realism(
            text, result.detected_seniority, profile
        )
        domain_score, d_str, d_gap = _score_domain_alignment(
            text, result.detected_domain, profile
        )
        work_mode_score, w_str, w_gap = _score_work_mode_alignment(
            result.detected_work_mode, profile
        )
        strategic_score, st_str, st_gap = _score_strategic_alignment(text, profile)
        portfolio_score, best_project, portfolio_highlights = _score_portfolio_alignment(
            text, profile.get("projects", [])
        )

        # ── Build breakdown ────────────────────────────────────────────────
        result.score_breakdown = {
            "title_relevance": title_score,
            "skill_overlap": skill_score,
            "seniority_realism": seniority_score,
            "domain_alignment": domain_score,
            "work_mode_alignment": work_mode_score,
            "strategic_alignment": strategic_score,
            "portfolio_alignment": portfolio_score,
        }

        # ── Weighted overall score (0–100) ─────────────────────────────────
        weighted = sum(
            _WEIGHTS[dim] * result.score_breakdown[dim]
            for dim in _WEIGHTS
        )
        result.overall_fit_score = round(weighted * 10.0, 1)

        # ── Strengths / Gaps / Risks ───────────────────────────────────────
        result.strengths = (
            t_str + s_str + d_str + w_str + st_str +
            ([f"Strong skill overlap: {', '.join(matched_skills[:4])}"] if len(matched_skills) >= 3 else []) +
            ([f"Portfolio match: '{best_project}'"] if best_project else [])
        )

        result.gaps = t_gap + s_gap + d_gap + w_gap + st_gap
        if missing_skills:
            result.gaps.append(f"Missing skills: {', '.join(missing_skills[:5])}")

        # ── Risks ──────────────────────────────────────────────────────────
        if seniority_score < 4.0:
            result.risks.append("Seniority bar may disqualify application at resume stage.")
        if work_mode_score <= 2.0:
            result.risks.append("Work mode incompatibility is a dealbreaker.")
        if len(missing_skills) > 6:
            result.risks.append("Too many skill gaps — application may be screened out.")

        # ── Gap analysis ───────────────────────────────────────────────────
        willingness = profile.get("willingness_to_learn", [])
        easy_gaps, hard_gaps = _classify_easy_vs_hard_gaps(missing_skills, willingness)
        result.easy_to_close_gaps = easy_gaps
        result.hard_to_close_gaps = hard_gaps
        result.gap_severity = _compute_gap_severity(missing_skills, hard_gaps)

        # ── Career direction alignment ─────────────────────────────────────
        preferred_domains = [d.lower() for d in profile.get("preferred_domains", [])]
        detected_lower = result.detected_domain.lower()
        if result.detected_domain and any(
            pd in detected_lower or detected_lower in pd for pd in preferred_domains
        ):
            result.career_direction_alignment = "aligned"
        elif result.detected_domain and any(
            any(w in detected_lower for w in pd.split("/"))
            for pd in preferred_domains
        ):
            result.career_direction_alignment = "partial"
        elif result.detected_domain:
            result.career_direction_alignment = "off-track"
        else:
            result.career_direction_alignment = "unknown"

        # ── Portfolio ──────────────────────────────────────────────────────
        result.best_matching_project = best_project
        result.portfolio_highlights = portfolio_highlights

        # ── Recommendation label ───────────────────────────────────────────
        result.recommendation_label, result.recommendation_reason = _assign_label(
            overall_score=result.overall_fit_score,
            gap_severity=result.gap_severity,
            seniority_score=seniority_score,
            work_mode_score=work_mode_score,
            career_direction_alignment=result.career_direction_alignment,
            hard_gaps=hard_gaps,
        )

        # ── Action items ───────────────────────────────────────────────────
        result.action_items = _build_action_items(
            label=result.recommendation_label,
            easy_gaps=easy_gaps,
            hard_gaps=hard_gaps,
            best_project=best_project,
            seniority_score=seniority_score,
            work_mode_score=work_mode_score,
        )

        logger.debug(
            "CareerScorer: job=%r score=%.1f label=%r",
            getattr(job, "title", ""),
            result.overall_fit_score,
            result.recommendation_label,
        )

        return result
