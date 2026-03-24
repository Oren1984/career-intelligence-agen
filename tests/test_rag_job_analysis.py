"""
Tests for app.services.rag_job_analysis

Covers: RAG-augmented job analysis, evidence augmentation, edge cases.
"""
import pytest

from app.rag.knowledge_service import KnowledgeService
from app.services.rag_job_analysis import (
    RAGJobAnalyzer,
    RAGAnalysisResult,
    _classify_evidence,
    _assess_coverage,
    _identify_missing_evidence,
)
from app.rag.retriever import RetrievedChunk


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_JOB = """
AI Engineer — Remote

We are looking for an experienced AI Engineer to join our team.

Requirements:
- 3+ years Python experience
- Experience with LLM applications and RAG systems
- Docker and Kubernetes for deployment
- AWS cloud infrastructure
- FastAPI for REST API development
- Experience with vector databases (ChromaDB, Pinecone)

Nice to have:
- MLOps pipeline experience
- Terraform for infrastructure
"""

SAMPLE_PROFILE = {
    "target_roles": ["AI Engineer", "LLM Engineer"],
    "experience_level": "mid",
    "skills": {
        "ai_ml": ["LLM", "RAG", "Embeddings"],
        "python": ["Python", "FastAPI"],
        "cloud_infra": ["AWS", "Docker"],
    },
    "summary": "Applied AI Engineer with RAG, LLM, Python, FastAPI, Docker, AWS experience.",
    "projects": [
        {
            "name": "RAG Bot",
            "description": "RAG system with LangChain and ChromaDB",
            "technologies": ["Python", "LangChain", "ChromaDB", "Docker"],
        }
    ],
    "work_mode_preference": "remote",
    "preferred_domains": ["AI/ML Engineering", "LLM Applications"],
}


@pytest.fixture
def sample_kb(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "skills").mkdir()

    (tmp_path / "projects" / "rag_bot.md").write_text(
        "# RAG Bot\n\nBuilt RAG system with LangChain, ChromaDB, FastAPI, Docker, AWS.",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "skills.md").write_text(
        "Skills: Python, FastAPI, Docker, AWS, LangChain, RAG, embeddings.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def rag_analyzer(sample_kb, tmp_path):
    index_dir = tmp_path / "index"
    ks = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    ks.ingest()
    return RAGJobAnalyzer(profile=SAMPLE_PROFILE, knowledge_service=ks)


@pytest.fixture
def rag_analyzer_no_kb(tmp_path):
    ks = KnowledgeService(
        kb_root=str(tmp_path / "empty"),
        index_dir=str(tmp_path / "index"),
    )
    return RAGJobAnalyzer(profile=SAMPLE_PROFILE, knowledge_service=ks)


# ── Tests: _classify_evidence ─────────────────────────────────────────────────

def _make_chunk(cat: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{cat}::chunk0", doc_id=cat, file_name="f.md",
        category=cat, text="content", score=0.5, chunk_index=0,
    )


def test_classify_evidence_projects():
    chunks = [_make_chunk("projects"), _make_chunk("skills"), _make_chunk("resume")]
    proj, skill, exp = _classify_evidence(chunks)
    assert len(proj) == 1
    assert len(skill) == 1
    assert len(exp) == 1


def test_classify_evidence_empty():
    proj, skill, exp = _classify_evidence([])
    assert proj == skill == exp == []


# ── Tests: _assess_coverage ───────────────────────────────────────────────────

def test_assess_coverage_none():
    assert _assess_coverage([]) == "none"


def test_assess_coverage_low():
    chunks = [RetrievedChunk("d::0", "d", "f.md", "c", "t", 0.01, 0)]
    assert _assess_coverage(chunks) == "low"


def test_assess_coverage_high():
    chunks = [
        RetrievedChunk(f"d::{i}", "d", "f.md", "c", "t", 0.15, i)
        for i in range(5)
    ]
    assert _assess_coverage(chunks) in ("high", "medium")


# ── Tests: _identify_missing_evidence ─────────────────────────────────────────

def test_identify_missing_evidence_with_gaps():
    gaps = ["Kubernetes experience", "Go programming language"]
    chunks = [
        RetrievedChunk("d::0", "d", "f.md", "c", "Python FastAPI Docker", 0.5, 0),
    ]
    notes = _identify_missing_evidence(gaps, chunks)
    # "Kubernetes" and "Go" not in chunks text, so should have notes
    assert len(notes) > 0


def test_identify_missing_evidence_no_gaps():
    notes = _identify_missing_evidence([], [])
    assert notes == []


def test_identify_missing_evidence_covered_gap():
    gaps = ["Python experience"]
    chunks = [
        RetrievedChunk("d::0", "d", "f.md", "c", "Python FastAPI Docker", 0.5, 0),
    ]
    notes = _identify_missing_evidence(gaps, chunks)
    # "Python" is in chunk text, so no missing note
    assert not any("Python" in n for n in notes)


# ── Tests: RAGJobAnalyzer ─────────────────────────────────────────────────────

def test_analyze_returns_result(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    assert isinstance(result, RAGAnalysisResult)


def test_analyze_has_base_scores(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    assert result.overall_fit_score >= 0
    assert result.recommendation_label != ""
    assert result.apply_decision in ("YES", "NO", "CONDITIONAL")


def test_analyze_has_rag_evidence(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    assert result.evidence_used
    assert len(result.retrieved_evidence) > 0
    assert result.kb_size > 0


def test_analyze_evidence_coverage(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    assert result.coverage in ("high", "medium", "low", "none")


def test_analyze_no_kb_graceful(rag_analyzer_no_kb):
    result = rag_analyzer_no_kb.analyze(SAMPLE_JOB)
    # Should still work, just without evidence
    assert isinstance(result, RAGAnalysisResult)
    assert result.overall_fit_score >= 0
    assert not result.evidence_used


def test_analyze_empty_job():
    ks = KnowledgeService(kb_root="/nonexistent", index_dir="/nonexistent")
    analyzer = RAGJobAnalyzer(profile={}, knowledge_service=ks)
    with pytest.raises(ValueError):
        analyzer.analyze("")


def test_analyze_with_title_and_company(rag_analyzer):
    result = rag_analyzer.analyze(
        SAMPLE_JOB,
        title="AI Engineer",
        company="Acme Inc.",
        location="Remote",
    )
    assert result.parsed_job.title == "AI Engineer"
    assert result.parsed_job.company == "Acme Inc."


def test_analyze_missing_evidence_notes(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    # missing_evidence_notes is a list (may be empty)
    assert isinstance(result.missing_evidence_notes, list)


def test_analyze_to_dict(rag_analyzer):
    result = rag_analyzer.analyze(SAMPLE_JOB)
    d = result.to_dict()
    assert "rag" in d
    assert "overall_fit_score" in d
    assert d["rag"]["kb_size"] > 0


def test_analyze_apply_only(rag_analyzer):
    out = rag_analyzer.analyze_apply_only(SAMPLE_JOB)
    assert "apply_decision" in out
    assert "evidence_used" in out
    assert out["apply_decision"] in ("YES", "NO", "CONDITIONAL")


def test_analyze_portfolio_only(rag_analyzer):
    out = rag_analyzer.analyze_portfolio_only(SAMPLE_JOB)
    assert "best_matching_project" in out
    assert "recommendation" in out


# ── Validation scenarios ──────────────────────────────────────────────────────

def test_scenario_strong_match(sample_kb, tmp_path):
    """Job strongly supported by portfolio."""
    index_dir = tmp_path / "index"
    ks = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    ks.ingest()
    analyzer = RAGJobAnalyzer(profile=SAMPLE_PROFILE, knowledge_service=ks)

    # Job closely matches the RAG bot project
    llm_job = "LLM Engineer with RAG, LangChain, ChromaDB, FastAPI, Docker, AWS"
    result = analyzer.analyze(llm_job)
    assert result.evidence_used
    # Should find evidence from projects/rag_bot.md


def test_scenario_weak_match(sample_kb, tmp_path):
    """Job description with no matching evidence."""
    index_dir = tmp_path / "index"
    ks = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    ks.ingest()
    analyzer = RAGJobAnalyzer(profile={}, knowledge_service=ks)

    # Completely unrelated job
    unrelated_job = "Ruby on Rails developer wanted for legacy e-commerce system"
    result = analyzer.analyze(unrelated_job)
    # May still have some evidence (if any terms overlap), but coverage should be low
    assert isinstance(result, RAGAnalysisResult)
