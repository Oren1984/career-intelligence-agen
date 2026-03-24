"""
Tests for app.rag.knowledge_service

Covers: ingest, retrieve, status, edge cases.
"""
import os
import pytest

from app.rag.knowledge_service import KnowledgeService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_kb(tmp_path):
    """Create a temporary knowledge base with sample documents."""
    (tmp_path / "resume").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "skills").mkdir()

    (tmp_path / "resume" / "cv.md").write_text(
        "# Resume\n\nExperienced AI Engineer with Python, FastAPI, Docker, and AWS experience.",
        encoding="utf-8",
    )
    (tmp_path / "projects" / "rag_bot.md").write_text(
        "# RAG Bot\n\nBuilt a retrieval-augmented generation system using LangChain, ChromaDB, and OpenAI.",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "skills.md").write_text(
        "## Core Skills\n\nPython, FastAPI, Docker, Kubernetes, AWS, LangChain, RAG, embeddings.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def empty_kb(tmp_path):
    """An empty knowledge base directory."""
    return tmp_path


@pytest.fixture
def service(sample_kb, tmp_path):
    """KnowledgeService pointing at sample KB with fresh index dir."""
    index_dir = tmp_path / "index"
    return KnowledgeService(
        kb_root=str(sample_kb),
        index_dir=str(index_dir),
    )


# ── Tests: ingest ─────────────────────────────────────────────────────────────

def test_ingest_basic(service):
    status = service.ingest()
    assert status.is_indexed
    assert status.total_documents >= 3
    assert status.total_chunks >= 3


def test_ingest_categories(service):
    status = service.ingest()
    assert "resume" in status.categories
    assert "projects" in status.categories
    assert "skills" in status.categories


def test_ingest_empty_kb(empty_kb, tmp_path):
    svc = KnowledgeService(kb_root=str(empty_kb), index_dir=str(tmp_path / "idx"))
    status = svc.ingest()
    assert not status.is_indexed


def test_ingest_nonexistent_kb(tmp_path):
    svc = KnowledgeService(
        kb_root=str(tmp_path / "nonexistent"),
        index_dir=str(tmp_path / "idx"),
    )
    status = svc.ingest()
    assert not status.is_indexed


def test_ingest_idempotent(service):
    status1 = service.ingest()
    status2 = service.ingest()  # Should skip (already indexed)
    assert status1.total_chunks == status2.total_chunks


def test_rebuild_forces_reingest(service):
    service.ingest()
    status = service.rebuild()
    assert status.is_indexed


# ── Tests: is_ready ───────────────────────────────────────────────────────────

def test_is_ready_after_ingest(service):
    assert not service.is_ready()  # Before ingest
    service.ingest()
    assert service.is_ready()


def test_is_ready_empty_kb(empty_kb, tmp_path):
    svc = KnowledgeService(kb_root=str(empty_kb), index_dir=str(tmp_path / "idx"))
    svc.ingest()
    assert not svc.is_ready()


# ── Tests: retrieve ───────────────────────────────────────────────────────────

def test_retrieve_basic(service):
    service.ingest()
    result = service.retrieve("Python FastAPI Docker")
    assert result.has_evidence()


def test_retrieve_relevant_chunks(service):
    service.ingest()
    result = service.retrieve("RAG LangChain embeddings")
    # The RAG bot project should be retrieved
    assert result.has_evidence()
    assert any("rag" in c.text.lower() or "langchain" in c.text.lower() for c in result.chunks)


def test_retrieve_not_ready(empty_kb, tmp_path):
    svc = KnowledgeService(kb_root=str(empty_kb), index_dir=str(tmp_path / "idx"))
    result = svc.retrieve("Python Docker")
    assert not result.has_evidence()
    assert result.kb_size == 0


def test_retrieve_category_filter(service):
    service.ingest()
    result = service.retrieve("Python Docker", categories=["resume"])
    for chunk in result.chunks:
        assert chunk.category == "resume"


def test_retrieve_for_job(service):
    service.ingest()
    job_desc = (
        "We are seeking an AI Engineer with experience in Python, FastAPI, "
        "Docker, and AWS. Must have RAG and LLM system experience."
    )
    result = service.retrieve_for_job(job_desc, top_k=5)
    assert result.has_evidence()


# ── Tests: get_status ────────────────────────────────────────────────────────

def test_get_status_before_ingest(service):
    status = service.get_status()
    assert not status.is_indexed
    assert status.total_chunks == 0


def test_get_status_after_ingest(service):
    service.ingest()
    status = service.get_status()
    assert status.is_indexed
    assert status.total_documents > 0
    assert status.total_chunks > 0
    assert len(status.categories) > 0


def test_get_status_has_kb_root(service):
    status = service.get_status()
    assert status.kb_root != ""


# ── Tests: index persistence ──────────────────────────────────────────────────

def test_index_persisted_to_disk(service, tmp_path):
    index_dir = tmp_path / "index"
    svc2 = KnowledgeService(
        kb_root=str(service._kb_root),
        index_dir=str(index_dir),
    )
    svc2.ingest()
    # Index file should exist
    assert (index_dir / "index.json").exists()


def test_index_loaded_on_new_instance(sample_kb, tmp_path):
    index_dir = tmp_path / "index"
    svc1 = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    svc1.ingest()

    # New instance should load existing index
    svc2 = KnowledgeService(kb_root=str(sample_kb), index_dir=str(index_dir))
    assert svc2.is_ready()
