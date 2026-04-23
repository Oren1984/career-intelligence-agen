"""
tests/test_execution_modes.py — Validate the three execution modes.

Covers:
- RAG Only: retrieval without scoring
- Agent Only: scoring without RAG retrieval
- Hybrid: scoring + RAG retrieval
- analyze_with_mode() dispatch logic
- RAGOnlyResult data model
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.rag_job_analysis import (
    RAGJobAnalyzer,
    RAGOnlyResult,
    RAGAnalysisResult,
)
from app.services.manual_job_analysis import ManualJobAnalyzer, ManualAnalysisResult
from app.rag.knowledge_service import KnowledgeService


SAMPLE_JOB = """
Senior AI Engineer — Remote

We are looking for an experienced AI Engineer.

Requirements:
- 3+ years Python experience
- LLM application development
- Docker and Kubernetes
- FastAPI REST API development
"""

SAMPLE_PROFILE = {
    "target_roles": ["AI Engineer", "LLM Engineer"],
    "experience_level": "mid",
    "skills": {
        "ai_ml": ["LLM", "RAG"],
        "python": ["Python", "FastAPI"],
        "cloud_infra": ["Docker"],
    },
    "summary": "AI Engineer with LLM, Python, FastAPI, Docker experience.",
    "projects": [
        {
            "name": "RAG Bot",
            "description": "RAG system with LangChain",
            "technologies": ["Python", "Docker"],
        }
    ],
    "work_mode_preference": "remote",
    "preferred_domains": ["AI/ML Engineering"],
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ks_ready():
    """KnowledgeService with KB indexed and returning dummy chunks."""
    from app.rag.retriever import RetrievedChunk, RetrievalResult

    dummy_chunk = RetrievedChunk(
        chunk_id="c1",
        doc_id="doc1",
        file_name="resume.md",
        category="resume",
        text="Python FastAPI RAG LLM experience",
        score=0.15,
        chunk_index=0,
    )
    dummy_retrieval = RetrievalResult(
        query="test query",
        chunks=[dummy_chunk],
        kb_size=50,
    )

    ks = MagicMock(spec=KnowledgeService)
    ks.is_ready.return_value = True
    ks.retrieve_for_job.return_value = dummy_retrieval
    return ks


@pytest.fixture
def mock_ks_empty():
    """KnowledgeService that is NOT indexed."""
    ks = MagicMock(spec=KnowledgeService)
    ks.is_ready.return_value = False
    return ks


@pytest.fixture
def analyzer_with_kb(mock_ks_ready):
    return RAGJobAnalyzer(profile=SAMPLE_PROFILE, knowledge_service=mock_ks_ready)


@pytest.fixture
def analyzer_no_kb(mock_ks_empty):
    return RAGJobAnalyzer(profile=SAMPLE_PROFILE, knowledge_service=mock_ks_empty)


# ── RAGOnlyResult model ───────────────────────────────────────────────────────

class TestRAGOnlyResult:
    def test_default_fields(self):
        r = RAGOnlyResult(raw_text="test")
        assert r.execution_mode == "rag_only"
        assert r.coverage == "none"
        assert r.kb_size == 0
        assert r.evidence_used is False
        assert r.retrieved_evidence == []
        assert r.missing_evidence_notes == []

    def test_to_dict(self):
        r = RAGOnlyResult(raw_text="test", coverage="high", kb_size=42)
        d = r.to_dict()
        assert d["execution_mode"] == "rag_only"
        assert d["coverage"] == "high"
        assert d["kb_size"] == 42
        assert "retrieved_evidence" in d
        assert "project_evidence" in d
        assert "skill_evidence" in d


# ── RAG Only mode ─────────────────────────────────────────────────────────────

class TestRAGOnlyMode:
    def test_analyze_rag_only_with_kb(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_rag_only(SAMPLE_JOB)

        assert isinstance(result, RAGOnlyResult)
        assert result.execution_mode == "rag_only"
        assert result.kb_size == 50
        assert len(result.retrieved_evidence) == 1
        assert result.evidence_used is True

    def test_analyze_rag_only_no_kb(self, analyzer_no_kb):
        result = analyzer_no_kb.analyze_rag_only(SAMPLE_JOB)

        assert isinstance(result, RAGOnlyResult)
        assert result.evidence_used is False
        assert len(result.missing_evidence_notes) > 0
        assert "not indexed" in result.missing_evidence_notes[0].lower()

    def test_rag_only_has_no_scoring(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_rag_only(SAMPLE_JOB)

        # RAGOnlyResult must NOT have career scoring fields
        assert not hasattr(result, "overall_fit_score")
        assert not hasattr(result, "recommendation_label")
        assert not hasattr(result, "gaps")
        assert not hasattr(result, "apply_decision")

    def test_analyze_with_mode_rag_only(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="rag_only")
        assert isinstance(result, RAGOnlyResult)


# ── Agent Only mode ───────────────────────────────────────────────────────────

class TestAgentOnlyMode:
    def test_analyze_with_mode_agent_only_returns_manual_result(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="agent_only")

        assert isinstance(result, ManualAnalysisResult)

    def test_agent_only_has_scoring(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="agent_only")

        assert isinstance(result.overall_fit_score, float)
        assert result.recommendation_label != ""
        assert isinstance(result.gaps, list)
        assert result.apply_decision in ("YES", "NO", "CONDITIONAL")

    def test_agent_only_does_not_call_ks(self, analyzer_with_kb, mock_ks_ready):
        analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="agent_only")

        # Knowledge service retrieve should NOT be called in agent_only mode
        mock_ks_ready.retrieve_for_job.assert_not_called()

    def test_agent_only_no_kb(self, analyzer_no_kb):
        result = analyzer_no_kb.analyze_with_mode(SAMPLE_JOB, mode="agent_only")

        # Works fine even without KB — scoring is rule-based
        assert isinstance(result, ManualAnalysisResult)
        assert result.overall_fit_score >= 0


# ── Hybrid mode ───────────────────────────────────────────────────────────────

class TestHybridMode:
    def test_analyze_with_mode_hybrid_returns_rag_result(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="hybrid")

        assert isinstance(result, RAGAnalysisResult)

    def test_hybrid_has_both_scoring_and_evidence(self, analyzer_with_kb):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="hybrid")

        # Has scoring fields (via base_result)
        assert result.overall_fit_score >= 0
        assert result.recommendation_label != ""

        # Has RAG evidence fields
        assert result.kb_size == 50
        assert result.evidence_used is True

    def test_hybrid_calls_kb_retrieval(self, analyzer_with_kb, mock_ks_ready):
        analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="hybrid")

        mock_ks_ready.retrieve_for_job.assert_called_once()

    def test_hybrid_default_mode(self, analyzer_with_kb):
        result_default = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB)
        result_explicit = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="hybrid")

        assert type(result_default) == type(result_explicit)


# ── Mode dispatch correctness ─────────────────────────────────────────────────

class TestModeDispatch:
    @pytest.mark.parametrize("mode,expected_type", [
        ("rag_only", RAGOnlyResult),
        ("agent_only", ManualAnalysisResult),
        ("hybrid", RAGAnalysisResult),
    ])
    def test_each_mode_returns_correct_type(self, analyzer_with_kb, mode, expected_type):
        result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode=mode)
        assert isinstance(result, expected_type), (
            f"Mode '{mode}' should return {expected_type.__name__}, got {type(result).__name__}"
        )

    def test_modes_are_independent(self, analyzer_with_kb):
        rag_result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="rag_only")
        agent_result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="agent_only")
        hybrid_result = analyzer_with_kb.analyze_with_mode(SAMPLE_JOB, mode="hybrid")

        assert isinstance(rag_result, RAGOnlyResult)
        assert isinstance(agent_result, ManualAnalysisResult)
        assert isinstance(hybrid_result, RAGAnalysisResult)
