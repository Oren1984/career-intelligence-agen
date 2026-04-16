"""Tests for personal_profile_service — load, save, validate, and profile-affects-results."""
import json
from pathlib import Path

import pytest

from app.services.personal_profile_service import (
    build_analysis_context,
    get_default_profile,
    load_personal_profile,
    profile_exists,
    save_personal_profile,
    validate_personal_profile,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_profile(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ── get_default_profile ───────────────────────────────────────────────────────

class TestGetDefaultProfile:
    def test_returns_dict(self):
        p = get_default_profile()
        assert isinstance(p, dict)

    def test_has_required_keys(self):
        p = get_default_profile()
        for key in [
            "name", "headline", "target_roles", "experience_level",
            "work_mode_preference", "strong_skills", "weak_skills",
            "willingness_to_learn", "preferred_technologies", "avoided_technologies",
            "career_tracks", "salary_preference", "portfolio_project_priorities",
            "resume_summary", "achievements_summary", "notes",
        ]:
            assert key in p, f"Missing key: {key}"

    def test_list_fields_are_lists(self):
        p = get_default_profile()
        for f in ["target_roles", "strong_skills", "weak_skills"]:
            assert isinstance(p[f], list)

    def test_career_tracks_is_dict(self):
        p = get_default_profile()
        assert isinstance(p["career_tracks"], dict)
        assert "primary" in p["career_tracks"]
        assert "acceptable" in p["career_tracks"]
        assert "avoid" in p["career_tracks"]


# ── validate_personal_profile ─────────────────────────────────────────────────

class TestValidatePersonalProfile:
    def test_valid_defaults_returns_no_errors(self):
        assert validate_personal_profile(get_default_profile()) == []

    def test_invalid_list_field_returns_error(self):
        p = get_default_profile()
        p["strong_skills"] = "Python"  # should be a list
        errors = validate_personal_profile(p)
        assert any("strong_skills" in e for e in errors)

    def test_invalid_experience_level_returns_error(self):
        p = get_default_profile()
        p["experience_level"] = "expert"
        errors = validate_personal_profile(p)
        assert any("experience_level" in e for e in errors)

    def test_valid_experience_levels_accepted(self):
        for level in ("", "junior", "mid", "senior"):
            p = get_default_profile()
            p["experience_level"] = level
            assert validate_personal_profile(p) == [], f"Level {level!r} should be valid"

    def test_invalid_work_mode_returns_error(self):
        p = get_default_profile()
        p["work_mode_preference"] = "full-time"
        errors = validate_personal_profile(p)
        assert any("work_mode_preference" in e for e in errors)

    def test_valid_work_modes_accepted(self):
        for mode in ("", "remote", "hybrid", "onsite", "any"):
            p = get_default_profile()
            p["work_mode_preference"] = mode
            assert validate_personal_profile(p) == [], f"Mode {mode!r} should be valid"

    def test_string_field_with_wrong_type_returns_error(self):
        p = get_default_profile()
        p["name"] = 123
        errors = validate_personal_profile(p)
        assert any("name" in e for e in errors)


# ── load_personal_profile ─────────────────────────────────────────────────────

class TestLoadPersonalProfile:
    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH",
                            tmp_path / "personal_profile.json")
        result = load_personal_profile()
        assert isinstance(result, dict)
        assert result["name"] == ""
        assert result["strong_skills"] == []

    def test_loads_stored_values(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        _write_profile(profile_file, {"name": "Alice", "strong_skills": ["Python", "Docker"]})
        result = load_personal_profile()
        assert result["name"] == "Alice"
        assert "Python" in result["strong_skills"]

    def test_merges_over_defaults(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        _write_profile(profile_file, {"name": "Bob"})
        result = load_personal_profile()
        # Defaults still present for unset fields
        assert result["headline"] == ""
        assert result["name"] == "Bob"

    def test_deep_merges_career_tracks(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        _write_profile(profile_file, {"career_tracks": {"primary": "AI Engineer"}})
        result = load_personal_profile()
        assert result["career_tracks"]["primary"] == "AI Engineer"
        # Default sub-keys still present
        assert "acceptable" in result["career_tracks"]

    def test_graceful_on_corrupt_json(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        profile_file.write_text("NOT JSON {{", encoding="utf-8")
        result = load_personal_profile()
        assert isinstance(result, dict)
        assert result["name"] == ""


# ── save_personal_profile ─────────────────────────────────────────────────────

class TestSavePersonalProfile:
    def test_saves_valid_profile(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "data" / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        p = get_default_profile()
        p["name"] = "Test User"
        save_personal_profile(p)
        assert profile_file.exists()
        stored = json.loads(profile_file.read_text())
        assert stored["name"] == "Test User"

    def test_raises_on_invalid_profile(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "data" / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        p = get_default_profile()
        p["experience_level"] = "god-tier"
        with pytest.raises(ValueError, match="experience_level"):
            save_personal_profile(p)

    def test_creates_parent_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "deep" / "nested" / "personal_profile.json"
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", nested)
        save_personal_profile(get_default_profile())
        assert nested.exists()


# ── profile_exists ────────────────────────────────────────────────────────────

class TestProfileExists:
    def test_returns_false_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH",
                            tmp_path / "personal_profile.json")
        assert profile_exists() is False

    def test_returns_true_when_present(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "personal_profile.json"
        profile_file.write_text("{}", encoding="utf-8")
        monkeypatch.setattr("app.services.personal_profile_service.PROFILE_PATH", profile_file)
        assert profile_exists() is True


# ── build_analysis_context ────────────────────────────────────────────────────

class TestBuildAnalysisContext:
    def test_empty_profile_returns_empty_string(self):
        assert build_analysis_context(get_default_profile()) == ""

    def test_includes_name(self):
        p = get_default_profile()
        p["name"] = "Alice"
        assert "Alice" in build_analysis_context(p)

    def test_includes_strong_skills(self):
        p = get_default_profile()
        p["strong_skills"] = ["Python", "RAG"]
        ctx = build_analysis_context(p)
        assert "Python" in ctx and "RAG" in ctx

    def test_includes_weak_skills(self):
        p = get_default_profile()
        p["weak_skills"] = ["Kubernetes"]
        assert "Kubernetes" in build_analysis_context(p)

    def test_includes_goals(self):
        p = get_default_profile()
        p["short_term_goal"] = "Land an AI role"
        p["long_term_goal"] = "Lead AI teams"
        ctx = build_analysis_context(p)
        assert "Land an AI role" in ctx
        assert "Lead AI teams" in ctx


# ── Profile affects analysis results ─────────────────────────────────────────

class TestProfileAffectsResults:
    """Validate that profile differences produce different analysis outputs."""

    def _make_sample_job(self):
        """Return a simple namespace object with .title and .description (as CareerScorer expects)."""
        from types import SimpleNamespace
        return SimpleNamespace(
            title="AI Engineer",
            description=(
                "We are looking for a Python AI Engineer with strong RAG and LLM experience. "
                "Must know Docker, FastAPI, and AWS. Kubernetes is a plus. "
                "Remote work available. Mid-level position."
            ),
            location="Remote",
        )

    def test_strong_skills_improve_career_score(self):
        """A profile with matching strong skills should score higher than one without."""
        from app.matching.career_scorer import CareerScorer

        job = self._make_sample_job()

        profile_with_skills = {
            "target_roles": ["AI Engineer"],
            "strong_skills": ["Python", "RAG", "LLM", "Docker", "FastAPI", "AWS"],
            "weak_skills": [],
            "experience_level": "mid",
            "work_mode_preference": "remote",
            "preferred_domains": [],
            "career_tracks": {"primary": "Applied AI / LLM Engineer", "acceptable": [], "avoid": []},
            "preferred_technologies": ["Python", "Docker", "FastAPI"],
            "avoided_technologies": [],
            "portfolio_project_priorities": [],
            "projects": [],
            "summary": "AI engineer with RAG and LLM experience.",
        }

        profile_no_skills = {
            "target_roles": ["Backend Developer"],
            "strong_skills": ["Java", "Spring", "Oracle"],
            "weak_skills": ["Python", "AI", "ML"],
            "experience_level": "mid",
            "work_mode_preference": "onsite",
            "preferred_domains": ["Finance"],
            "career_tracks": {"primary": "Backend Java", "acceptable": [], "avoid": ["AI"]},
            "preferred_technologies": ["Java", "Spring"],
            "avoided_technologies": ["Python", "Docker"],
            "portfolio_project_priorities": [],
            "projects": [],
            "summary": "Java backend developer, no AI experience.",
        }

        scorer_good = CareerScorer(profile=profile_with_skills)
        scorer_bad = CareerScorer(profile=profile_no_skills)

        result_good = scorer_good.score(job)
        result_bad = scorer_bad.score(job)

        assert result_good.overall_fit_score > result_bad.overall_fit_score, (
            f"Profile with matching skills should score higher: "
            f"{result_good.overall_fit_score} vs {result_bad.overall_fit_score}"
        )

    def test_weak_skills_increase_gaps(self):
        """Declaring a required skill as weak should increase identified gaps."""
        from app.matching.gap_analyzer import GapAnalyzer

        job = self._make_sample_job()

        profile_strong_docker = {
            "strong_skills": ["Python", "Docker", "FastAPI", "RAG"],
            "weak_skills": [],
        }
        profile_weak_docker = {
            "strong_skills": ["Python", "FastAPI", "RAG"],
            "weak_skills": ["Docker"],
        }

        gaps_strong = GapAnalyzer(profile=profile_strong_docker).analyze(job)
        gaps_weak = GapAnalyzer(profile=profile_weak_docker).analyze(job)

        # When Docker is declared weak, it should appear in gaps or gap count should increase
        all_gaps_weak = [g.skill.lower() for g in gaps_weak.all_gaps]
        assert (
            "docker" in all_gaps_weak
            or len(gaps_weak.all_gaps) >= len(gaps_strong.all_gaps)
        ), "Declaring Docker as weak should show Docker in gaps"

    def test_target_roles_affect_title_relevance(self):
        """Profile targeting the right role should get higher title relevance."""
        from app.matching.career_scorer import CareerScorer

        job = self._make_sample_job()

        profile_ai = {
            "target_roles": ["AI Engineer", "LLM Engineer"],
            "strong_skills": ["Python"],
            "weak_skills": [],
            "experience_level": "mid",
            "work_mode_preference": "any",
            "preferred_domains": [],
            "career_tracks": {"primary": "AI Engineer", "acceptable": [], "avoid": []},
            "preferred_technologies": [],
            "avoided_technologies": [],
            "portfolio_project_priorities": [],
            "projects": [],
            "summary": "",
        }

        profile_other = {
            "target_roles": ["Data Analyst", "Business Intelligence"],
            "strong_skills": ["Python"],
            "weak_skills": [],
            "experience_level": "mid",
            "work_mode_preference": "any",
            "preferred_domains": [],
            "career_tracks": {"primary": "Data Analyst", "acceptable": [], "avoid": []},
            "preferred_technologies": [],
            "avoided_technologies": [],
            "portfolio_project_priorities": [],
            "projects": [],
            "summary": "",
        }

        score_ai = CareerScorer(profile=profile_ai).score(job)
        score_other = CareerScorer(profile=profile_other).score(job)

        # Title relevance dimension should be higher for AI-targeting profile
        ai_title_score = score_ai.score_breakdown.get("title_relevance", 0)
        other_title_score = score_other.score_breakdown.get("title_relevance", 0)

        assert ai_title_score >= other_title_score, (
            f"AI target roles should yield higher title relevance: {ai_title_score} vs {other_title_score}"
        )
