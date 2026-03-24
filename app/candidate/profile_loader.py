# candidate/profile_loader.py
# Defines CandidateProfile dataclass and load_candidate_profile function.

"""Candidate profile loader — reads structured profile files and builds a unified CandidateProfile."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE_DIR = Path(__file__).parent.parent.parent / "data" / "candidate_profile"
_CONFIG_PROFILE_PATH = Path(__file__).parent.parent.parent / "config" / "profile.yaml"


@dataclass
class CandidateProfile:
    """
    Unified candidate profile built from:
      - config/profile.yaml    (roles, keywords, preferences, goals)
      - data/candidate_profile/summary.txt   (free-text summary)
      - data/candidate_profile/skills.json   (structured skills)
      - data/candidate_profile/projects.json (project examples)
    """

    # ── Core Role Targeting ──────────────────────────────────────────────────
    target_roles: list[str] = field(default_factory=list)
    preferred_role_track: str = ""
    experience_level: str = "mid"          # junior | mid | senior
    seniority_target: str = "mid"

    # ── Keywords ────────────────────────────────────────────────────────────
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)

    # ── Technologies ────────────────────────────────────────────────────────
    preferred_technologies: list[str] = field(default_factory=list)
    avoided_technologies: list[str] = field(default_factory=list)

    # ── Location & Work Mode ─────────────────────────────────────────────────
    preferred_locations: list[str] = field(default_factory=list)
    work_mode_preference: str = "any"      # remote | hybrid | onsite | any

    # ── Preferences ──────────────────────────────────────────────────────────
    company_type_preference: list[str] = field(default_factory=list)
    language_preference: str = "english"
    salary_preference: dict[str, Any] = field(default_factory=dict)

    # ── Career Direction ─────────────────────────────────────────────────────
    short_term_goal: str = ""
    long_term_goal: str = ""
    preferred_domains: list[str] = field(default_factory=list)
    willingness_to_learn: list[str] = field(default_factory=list)

    # ── Career Tracks ────────────────────────────────────────────────────────
    career_tracks: dict[str, Any] = field(default_factory=dict)

    # ── Profile Data Files ───────────────────────────────────────────────────
    summary: str = ""
    skills: dict[str, list[str]] = field(default_factory=dict)
    projects: list[dict[str, Any]] = field(default_factory=list)

    # ── Convenience Properties ───────────────────────────────────────────────

    @property
    def all_skills(self) -> list[str]:
        """Flat list of all skills across all categories."""
        result: list[str] = []
        for skill_list in self.skills.values():
            result.extend(skill_list)
        return result

    @property
    def all_skills_lower(self) -> list[str]:
        """Flat list of all skills, lowercased for matching."""
        return [s.lower() for s in self.all_skills]

    @property
    def preferred_technologies_lower(self) -> list[str]:
        return [t.lower() for t in self.preferred_technologies]

    @property
    def avoided_technologies_lower(self) -> list[str]:
        return [t.lower() for t in self.avoided_technologies]

    @property
    def all_portfolio_technologies(self) -> list[str]:
        """All unique technologies mentioned across all portfolio projects."""
        techs: list[str] = []
        for project in self.projects:
            techs.extend(project.get("technologies", []))
        return list(set(techs))

    @property
    def primary_track(self) -> str:
        """Primary career track from career_tracks config."""
        return self.career_tracks.get("primary", self.preferred_role_track or "")

    @property
    def acceptable_tracks(self) -> list[str]:
        return self.career_tracks.get("acceptable", [])

    @property
    def avoided_tracks(self) -> list[str]:
        return self.career_tracks.get("avoid", [])

    def to_prompt_string(self) -> str:
        """Build a concise profile summary suitable for LLM prompts."""
        parts: list[str] = []

        if self.summary:
            parts.append(f"Summary: {self.summary}")

        if self.target_roles:
            parts.append(f"Target Roles: {', '.join(self.target_roles)}")

        if self.all_skills:
            parts.append(f"Key Skills: {', '.join(self.all_skills[:20])}")
        elif self.positive_keywords:
            parts.append(f"Key Skills: {', '.join(self.positive_keywords)}")

        if self.projects:
            project_names = [p.get("name", "Unnamed") for p in self.projects[:3]]
            parts.append(f"Recent Projects: {', '.join(project_names)}")

        if self.short_term_goal:
            parts.append(f"Short-term Goal: {self.short_term_goal.strip()}")

        if self.preferred_domains:
            parts.append(f"Preferred Domains: {', '.join(self.preferred_domains)}")

        if self.negative_keywords:
            parts.append(f"Not targeting: {', '.join(self.negative_keywords)} roles")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_roles": self.target_roles,
            "preferred_role_track": self.preferred_role_track,
            "experience_level": self.experience_level,
            "seniority_target": self.seniority_target,
            "positive_keywords": self.positive_keywords,
            "negative_keywords": self.negative_keywords,
            "preferred_technologies": self.preferred_technologies,
            "avoided_technologies": self.avoided_technologies,
            "preferred_locations": self.preferred_locations,
            "work_mode_preference": self.work_mode_preference,
            "company_type_preference": self.company_type_preference,
            "language_preference": self.language_preference,
            "salary_preference": self.salary_preference,
            "short_term_goal": self.short_term_goal,
            "long_term_goal": self.long_term_goal,
            "preferred_domains": self.preferred_domains,
            "willingness_to_learn": self.willingness_to_learn,
            "career_tracks": self.career_tracks,
            "summary": self.summary,
            "skills": self.skills,
            "projects": self.projects,
        }


def load_candidate_profile(
    profile_dir: str | Path | None = None,
    config_path: str | Path | None = None,
) -> CandidateProfile:
    """
    Load the candidate profile from disk.

    Reads (in order, all optional):
      1. config/profile.yaml      → roles, keywords, preferences, goals
      2. data/candidate_profile/summary.txt   → free-text summary
      3. data/candidate_profile/skills.json   → structured skills
      4. data/candidate_profile/projects.json → projects

    Missing files are silently skipped; defaults are empty.
    """
    profile = CandidateProfile()

    # 1. Load config/profile.yaml
    cfg_path = Path(config_path or _CONFIG_PROFILE_PATH)
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            profile.target_roles = cfg.get("target_roles", [])
            profile.positive_keywords = cfg.get("positive_keywords", [])
            profile.negative_keywords = cfg.get("negative_keywords", [])

            # New V2 fields
            profile.preferred_role_track = cfg.get("preferred_role_track", "")
            profile.experience_level = cfg.get("experience_level", "mid")
            profile.seniority_target = cfg.get("seniority_target", "mid")
            profile.preferred_technologies = cfg.get("preferred_technologies", [])
            profile.avoided_technologies = cfg.get("avoided_technologies", [])
            profile.preferred_locations = cfg.get("preferred_locations", [])
            profile.work_mode_preference = cfg.get("work_mode_preference", "any")
            profile.company_type_preference = cfg.get("company_type_preference", [])
            profile.language_preference = cfg.get("language_preference", "english")
            profile.salary_preference = cfg.get("salary_preference", {}) or {}
            profile.short_term_goal = cfg.get("short_term_goal", "")
            profile.long_term_goal = cfg.get("long_term_goal", "")
            profile.preferred_domains = cfg.get("preferred_domains", [])
            profile.willingness_to_learn = cfg.get("willingness_to_learn", [])
            profile.career_tracks = cfg.get("career_tracks", {}) or {}

            logger.debug("Loaded profile config from %s", cfg_path)
        except Exception as exc:
            logger.warning("Could not read %s: %s", cfg_path, exc)

    # 2–4. Load data/candidate_profile/ files
    p_dir = Path(profile_dir or _DEFAULT_PROFILE_DIR)

    summary_path = p_dir / "summary.txt"
    if summary_path.exists():
        try:
            profile.summary = summary_path.read_text(encoding="utf-8").strip()
            logger.debug("Loaded candidate summary from %s", summary_path)
        except Exception as exc:
            logger.warning("Could not read %s: %s", summary_path, exc)

    skills_path = p_dir / "skills.json"
    if skills_path.exists():
        try:
            with open(skills_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                profile.skills = data
            elif isinstance(data, list):
                profile.skills = {"skills": data}
            logger.debug("Loaded candidate skills from %s", skills_path)
        except Exception as exc:
            logger.warning("Could not read %s: %s", skills_path, exc)

    projects_path = p_dir / "projects.json"
    if projects_path.exists():
        try:
            with open(projects_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                profile.projects = data
            logger.debug("Loaded candidate projects from %s", projects_path)
        except Exception as exc:
            logger.warning("Could not read %s: %s", projects_path, exc)

    return profile
