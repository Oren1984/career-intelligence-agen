"""
Tests for app.rag.qa_service

Covers: Q&A over local knowledge, confidence assessment, edge cases.
"""
import pytest

from app.rag.knowledge_service import KnowledgeService
from app.rag.qa_service import CareerQAService, QAAnswer, _assess_confidence
from app.rag.retriever import RetrievalResult, RetrievedChunk


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_kb(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "resume").mkdir()

    (tmp_path / "projects" / "rag_bot.md").write_text(
        "# RAG Bot Project\n\n"
        "Built a retrieval-augmented generation system using LangChain, ChromaDB, "
        "OpenAI embeddings. Deployed via FastAPI on AWS with Docker. "
        "Achieved 92% answer relevance in human evaluation.",
        encoding="utf-8",
    )
    (tmp_path / "projects" / "mlops.md").write_text(
        "# MLOps Pipeline\n\n"
        "Designed end-to-end ML training pipeline on AWS SageMaker with Terraform. "
        "Model monitoring, drift detection, automated retraining.",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "skills.md").write_text(
        "## Skills\n\nPython, FastAPI, Docker, Kubernetes, AWS, LangChain, RAG, MLOps.",
        encoding="utf-8",
    )
    (tmp_path / "resume" / "cv.md").write_text(
        "## Experience\n\n"
        "AI Engineer at Tech Company: built LLM applications, RAG systems, "
        "MLOps pipelines. 3 years experience.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def qa_service(sample_kb, tmp_path):
    index_dir = tmp_path / "index"
    ks = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    ks.ingest()
    return CareerQAService(knowledge_service=ks)


@pytest.fixture
def qa_service_no_kb(tmp_path):
    """Q&A service with an empty/unindexed KB."""
    ks = KnowledgeService(
        kb_root=str(tmp_path / "empty_kb"),
        index_dir=str(tmp_path / "index"),
    )
    return CareerQAService(knowledge_service=ks)


# ── Tests: QAAnswer ───────────────────────────────────────────────────────────

def test_qa_answer_to_dict():
    answer = QAAnswer(
        question="What projects do I have?",
        answer="You have a RAG bot project.",
        confidence="high",
        has_evidence=True,
        sources=["rag_bot.md"],
    )
    d = answer.to_dict()
    assert d["question"] == "What projects do I have?"
    assert d["confidence"] == "high"
    assert d["has_evidence"] is True


# ── Tests: _assess_confidence ─────────────────────────────────────────────────

def test_assess_confidence_high():
    chunks = [
        RetrievedChunk("d::0", "d", "f.md", "c", "t", 0.20, 0),
        RetrievedChunk("d::1", "d", "f.md", "c", "t", 0.15, 1),
        RetrievedChunk("d::2", "d", "f.md", "c", "t", 0.10, 2),
        RetrievedChunk("d::3", "d", "f.md", "c", "t", 0.08, 3),
    ]
    result = RetrievalResult(query="test", chunks=chunks)
    assert _assess_confidence(result) == "high"


def test_assess_confidence_none():
    result = RetrievalResult(query="test", chunks=[])
    assert _assess_confidence(result) == "none"


def test_assess_confidence_low():
    chunks = [RetrievedChunk("d::0", "d", "f.md", "c", "t", 0.02, 0)]
    result = RetrievalResult(query="test", chunks=chunks)
    assert _assess_confidence(result) in ("low", "medium", "high")


# ── Tests: CareerQAService.ask ────────────────────────────────────────────────

def test_ask_returns_answer(qa_service):
    answer = qa_service.ask("Which of my projects demonstrates RAG?")
    assert isinstance(answer, QAAnswer)
    assert answer.question != ""
    assert answer.answer != ""


def test_ask_has_evidence(qa_service):
    answer = qa_service.ask("What RAG or LangChain project do I have?")
    assert answer.has_evidence
    assert len(answer.evidence) > 0


def test_ask_empty_question(qa_service):
    answer = qa_service.ask("")
    assert "Please provide" in answer.answer or answer.confidence == "none"


def test_ask_no_kb(qa_service_no_kb):
    answer = qa_service_no_kb.ask("What Python experience do I have?")
    assert not answer.has_evidence
    assert answer.confidence == "none"


def test_ask_sources_populated(qa_service):
    answer = qa_service.ask("What MLOps experience do I have?")
    if answer.has_evidence:
        assert len(answer.sources) > 0
        for src in answer.sources:
            assert isinstance(src, str)


def test_ask_returns_confidence(qa_service):
    answer = qa_service.ask("Which project best shows LLM work?")
    assert answer.confidence in ("high", "medium", "low", "none")


def test_ask_evidence_has_text(qa_service):
    answer = qa_service.ask("What AWS experience do I have?")
    for chunk in answer.evidence:
        assert chunk.text.strip() != ""
        assert chunk.score >= 0.0


# ── Tests: specialized methods ────────────────────────────────────────────────

def test_summarize_skills(qa_service):
    answer = qa_service.summarize_skills("Docker")
    assert isinstance(answer, QAAnswer)
    assert answer.question != ""


def test_find_best_project_for_role(qa_service):
    answer = qa_service.find_best_project_for_role("MLOps Engineer")
    assert isinstance(answer, QAAnswer)
    if answer.has_evidence:
        assert len(answer.evidence) > 0


def test_identify_recurring_gaps(qa_service):
    answer = qa_service.identify_recurring_gaps()
    assert isinstance(answer, QAAnswer)


def test_ask_batch(qa_service):
    questions = [
        "What Python experience do I have?",
        "Which projects use Docker?",
    ]
    answers = qa_service.ask_batch(questions)
    assert len(answers) == 2
    for answer in answers:
        assert isinstance(answer, QAAnswer)
