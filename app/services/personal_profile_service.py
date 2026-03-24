"""
personal_profile_service.py — Local Personal Profile management.

Manages a local JSON-based personal profile stored at
data/personal_profile.json (gitignored — never committed).

The personal profile overlays and extends config/profile.yaml:
- New fields (name, headline, strong_skills, weak_skills, etc.) live here.
- Existing fields (target_roles, experience_level, etc.) can be overridden here.
- Missing fields in the personal profile fall back to profile.yaml values.

Usage:
    from app.services.personal_profile_service import (
        load_personal_profile, save_personal_profile, validate_personal_profile
    )
    data = load_personal_profile()
    save_personal_profile(data)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
PROFILE_PATH = _REPO_ROOT / "data" / "personal_profile.json"


# ── Schema defaults ───────────────────────────────────────────────────────────

def get_default_profile() -> dict[str, Any]:
    """Return a clean default personal profile with all supported fields."""
    return {
        # ── Personal Identity ─────────────────────────────────────────────
        "name": "",
        "headline": "",          # e.g. "AI Engineer | MLOps | Python"

        # ── Role Targeting ────────────────────────────────────────────────
        # Leave empty to use config/profile.yaml values
        "target_roles": [],
        "experience_level": "",  # ""|"junior"|"mid"|"senior"
        "work_mode_preference": "",  # ""|"remote"|"hybrid"|"onsite"|"any"
        "preferred_locations": [],
        "preferred_domains": [],

        # ── Skills ───────────────────────────────────────────────────────
        "strong_skills": [],     # Skills you are highly confident in
        "weak_skills": [],       # Known weak areas — flagged in gap analysis
        "willingness_to_learn": [],

        # ── Technologies ─────────────────────────────────────────────────
        "preferred_technologies": [],
        "avoided_technologies": [],

        # ── Career Direction ──────────────────────────────────────────────
        "short_term_goal": "",
        "long_term_goal": "",

        # ── Career Tracks ─────────────────────────────────────────────────
        "career_tracks": {
            "primary": "",
            "acceptable": [],
            "avoid": [],
        },

        # ── Company & Salary ─────────────────────────────────────────────
        "company_type_preference": [],
        "salary_preference": {"min": "", "currency": ""},

        # ── Portfolio ────────────────────────────────────────────────────
        # Ordered list of project names — higher in list = higher priority
        "portfolio_project_priorities": [],

        # ── Summaries (used in RAG context) ──────────────────────────────
        "resume_summary": "",
        "achievements_summary": "",
        "notes": "",
    }


# ── Load / Save ───────────────────────────────────────────────────────────────

def load_personal_profile() -> dict[str, Any]:
    """
    Load the personal profile from disk.

    Returns the stored profile merged over defaults.
    Never raises — returns clean defaults if file is missing or corrupt.
    """
    defaults = get_default_profile()

    if not PROFILE_PATH.exists():
        logger.debug("No personal profile at %s — returning defaults.", PROFILE_PATH)
        return defaults

    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            stored: dict[str, Any] = json.load(f)

        merged = defaults.copy()
        for key, val in stored.items():
            if key in merged:
                merged[key] = val

        # Deep-merge nested dicts so we don't lose sub-keys
        for nested_key in ("career_tracks", "salary_preference"):
            if nested_key in stored and isinstance(stored[nested_key], dict):
                base = defaults.get(nested_key, {})
                merged[nested_key] = {**base, **stored[nested_key]}

        return merged

    except Exception as exc:
        logger.warning("Could not load personal profile: %s", exc)
        return defaults


def save_personal_profile(data: dict[str, Any]) -> None:
    """
    Validate then persist the personal profile to disk.

    Creates data/ directory if needed.
    Raises ValueError if validation fails.
    """
    errors = validate_personal_profile(data)
    if errors:
        raise ValueError(f"Profile validation failed:\n" + "\n".join(f"  • {e}" for e in errors))

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Personal profile saved to %s", PROFILE_PATH)


def validate_personal_profile(data: dict[str, Any]) -> list[str]:
    """
    Validate profile data.

    Returns a list of human-readable error messages.
    An empty list means the data is valid.
    """
    errors: list[str] = []

    # List fields
    list_fields = [
        "target_roles", "strong_skills", "weak_skills", "willingness_to_learn",
        "preferred_technologies", "avoided_technologies", "preferred_locations",
        "preferred_domains", "portfolio_project_priorities", "company_type_preference",
    ]
    for field in list_fields:
        if field in data and not isinstance(data[field], list):
            errors.append(f"'{field}' must be a list, got {type(data[field]).__name__}")

    # String fields
    str_fields = ["name", "headline", "short_term_goal", "long_term_goal",
                  "resume_summary", "achievements_summary", "notes"]
    for field in str_fields:
        if field in data and not isinstance(data[field], (str, type(None))):
            errors.append(f"'{field}' must be a string")

    # Enum fields
    valid_exp = ("", "junior", "mid", "senior")
    if data.get("experience_level", "") not in valid_exp:
        errors.append(
            f"experience_level must be one of: {', '.join(repr(v) for v in valid_exp)}"
        )

    valid_mode = ("", "remote", "hybrid", "onsite", "any")
    if data.get("work_mode_preference", "") not in valid_mode:
        errors.append(
            f"work_mode_preference must be one of: {', '.join(repr(v) for v in valid_mode)}"
        )

    return errors


# ── Helpers ───────────────────────────────────────────────────────────────────

def profile_exists() -> bool:
    """Return True if a personal profile file exists on disk."""
    return PROFILE_PATH.exists()


def get_profile_path() -> Path:
    """Return the filesystem path to the personal profile file."""
    return PROFILE_PATH


def build_analysis_context(profile: dict[str, Any]) -> str:
    """
    Build a concise text context from the personal profile for RAG / LLM analysis.

    Returns a string suitable for inclusion in prompts or evidence context.
    """
    parts: list[str] = []

    if profile.get("name"):
        parts.append(f"Candidate: {profile['name']}")
    if profile.get("headline"):
        parts.append(f"Headline: {profile['headline']}")
    if profile.get("strong_skills"):
        parts.append(f"Strong skills: {', '.join(profile['strong_skills'])}")
    if profile.get("weak_skills"):
        parts.append(f"Known weak areas: {', '.join(profile['weak_skills'])}")
    if profile.get("resume_summary"):
        parts.append(f"Resume summary: {profile['resume_summary']}")
    if profile.get("achievements_summary"):
        parts.append(f"Key achievements: {profile['achievements_summary']}")
    if profile.get("short_term_goal"):
        parts.append(f"Short-term goal: {profile['short_term_goal']}")
    if profile.get("long_term_goal"):
        parts.append(f"Long-term goal: {profile['long_term_goal']}")

    return "\n".join(parts)
