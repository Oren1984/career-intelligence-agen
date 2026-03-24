"""
Tests for app.rag.retriever

Covers: retrieval, scoring, deduplication, edge cases.
"""
import pytest

from app.rag.chunker import DocumentChunk
from app.rag.indexer import build_index, LocalIndex
from app.rag.retriever import KnowledgeRetriever, RetrievalResult, RetrievedChunk


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_chunk(chunk_id: str, text: str, category: str = "general") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("::")[0],
        file_name="test.md",
        category=category,
        text=text,
        chunk_index=0,
    )


@pytest.fixture
def populated_index():
    chunks = [
        _make_chunk("resume::chunk0", "Python FastAPI Docker AWS backend API development experience", "resume"),
        _make_chunk("projects::chunk0", "RAG LangChain embeddings vector ChromaDB LLM retrieval project", "projects"),
        _make_chunk("projects::chunk1", "MLOps pipeline Terraform Kubernetes SageMaker deployment", "projects"),
        _make_chunk("skills::chunk0", "Docker Kubernetes container orchestration DevOps infrastructure", "skills"),
        _make_chunk("strategy::chunk0", "Career goals AI engineer remote work target roles applied", "strategy"),
    ]
    return build_index(chunks)


@pytest.fixture
def empty_index():
    return build_index([])


# ── Tests: RetrievedChunk ─────────────────────────────────────────────────────

def test_retrieved_chunk_to_dict():
    chunk = RetrievedChunk(
        chunk_id="doc::chunk0",
        doc_id="doc",
        file_name="doc.md",
        category="projects",
        text="Some text",
        score=0.75,
        chunk_index=0,
    )
    d = chunk.to_dict()
    assert d["chunk_id"] == "doc::chunk0"
    assert d["score"] == pytest.approx(0.75, abs=0.001)
    assert d["category"] == "projects"


def test_retrieved_chunk_short_summary():
    chunk = RetrievedChunk(
        chunk_id="doc::chunk0",
        doc_id="doc",
        file_name="doc.md",
        category="resume",
        text="Python FastAPI Docker AWS",
        score=0.5,
        chunk_index=0,
    )
    summary = chunk.short_summary()
    assert "resume" in summary
    assert "doc.md" in summary


# ── Tests: RetrievalResult ────────────────────────────────────────────────────

def test_retrieval_result_has_evidence():
    result = RetrievalResult(
        query="test",
        chunks=[RetrievedChunk("x::0", "x", "x.md", "general", "text", 0.5, 0)],
    )
    assert result.has_evidence()


def test_retrieval_result_empty():
    result = RetrievalResult(query="test", chunks=[])
    assert not result.has_evidence()
    assert result.top_chunk() is None


def test_retrieval_result_as_context_string():
    chunks = [
        RetrievedChunk("doc::chunk0", "doc", "doc.md", "resume", "Python FastAPI Docker", 0.8, 0),
    ]
    result = RetrievalResult(query="python", chunks=chunks)
    ctx = result.as_context_string()
    assert "Python" in ctx or "FastAPI" in ctx
    assert "resume" in ctx


def test_retrieval_result_empty_context():
    result = RetrievalResult(query="test", chunks=[])
    ctx = result.as_context_string()
    assert "No relevant evidence" in ctx


# ── Tests: KnowledgeRetriever.retrieve ────────────────────────────────────────

def test_retrieve_returns_results(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("RAG LangChain embeddings")
    assert result.has_evidence()


def test_retrieve_top_k_respected(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("Python Docker AWS", top_k=2)
    assert len(result.chunks) <= 2


def test_retrieve_descending_scores(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("Python FastAPI Docker")
    scores = [c.score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_empty_query(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("")
    # Empty query should return no results
    assert len(result.chunks) == 0


def test_retrieve_empty_index(empty_index):
    retriever = KnowledgeRetriever(empty_index)
    result = retriever.retrieve("Python Docker")
    assert not result.has_evidence()
    assert result.kb_size == 0


def test_retrieve_category_filter(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("Docker Kubernetes", top_k=5, categories=["skills"])
    for chunk in result.chunks:
        assert chunk.category == "skills"


def test_retrieve_no_match_returns_empty(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    result = retriever.retrieve("zzzunknownterm9999")
    assert not result.has_evidence()


# ── Tests: KnowledgeRetriever.retrieve_for_job ───────────────────────────────

def test_retrieve_for_job_returns_evidence(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    job_desc = (
        "We are looking for an AI Engineer with experience in Python, FastAPI, "
        "Docker, and AWS. Experience with RAG and LLM systems is preferred."
    )
    result = retriever.retrieve_for_job(job_desc, top_k=5)
    assert result.has_evidence()


def test_retrieve_for_job_no_duplicates(populated_index):
    retriever = KnowledgeRetriever(populated_index)
    job_desc = "Python Docker AWS Kubernetes RAG embeddings LangChain MLOps Terraform"
    result = retriever.retrieve_for_job(job_desc, top_k=10)
    chunk_ids = [c.chunk_id for c in result.chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunks in results"
