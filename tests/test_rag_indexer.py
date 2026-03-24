"""
Tests for app.rag.indexer

Covers: index building, TF-IDF computation, save/load, querying.
"""
import json
import os
import pytest

from app.rag.chunker import DocumentChunk
from app.rag.indexer import (
    build_index,
    save_index,
    load_index,
    query_index,
    _tokenize,
    _compute_tf,
    _cosine_similarity,
    LocalIndex,
)


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
def sample_chunks():
    return [
        _make_chunk("doc1::chunk0", "Python FastAPI Docker AWS cloud engineering backend development", "experience"),
        _make_chunk("doc2::chunk0", "RAG LangChain embeddings vector database ChromaDB LLM retrieval", "projects"),
        _make_chunk("doc3::chunk0", "MLOps pipeline SageMaker Terraform Kubernetes model training deployment", "projects"),
        _make_chunk("doc4::chunk0", "Data engineering SQL PostgreSQL Redis data pipelines processing", "skills"),
        _make_chunk("doc5::chunk0", "Career goals target roles AI engineer remote work Python", "strategy"),
    ]


# ── Tests: _tokenize ─────────────────────────────────────────────────────────

def test_tokenize_basic():
    tokens = _tokenize("Python FastAPI Docker AWS")
    assert "python" in tokens
    assert "fastapi" in tokens
    assert "docker" in tokens
    assert "aws" in tokens


def test_tokenize_removes_stop_words():
    tokens = _tokenize("the and or is it to for a an")
    assert tokens == []


def test_tokenize_lowercases():
    tokens = _tokenize("Python DOCKER Kubernetes")
    assert all(t == t.lower() for t in tokens)


def test_tokenize_empty():
    assert _tokenize("") == []


# ── Tests: _compute_tf ────────────────────────────────────────────────────────

def test_compute_tf_basic():
    tf = _compute_tf(["python", "python", "docker"])
    assert tf["python"] == pytest.approx(2 / 3)
    assert tf["docker"] == pytest.approx(1 / 3)


def test_compute_tf_empty():
    tf = _compute_tf([])
    assert tf == {}


# ── Tests: _cosine_similarity ─────────────────────────────────────────────────

def test_cosine_similarity_identical():
    vec = {"python": 0.5, "docker": 0.3}
    assert _cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    vec_a = {"python": 1.0}
    vec_b = {"docker": 1.0}
    assert _cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)


def test_cosine_similarity_empty():
    assert _cosine_similarity({}, {"python": 1.0}) == pytest.approx(0.0)
    assert _cosine_similarity({"python": 1.0}, {}) == pytest.approx(0.0)


# ── Tests: build_index ────────────────────────────────────────────────────────

def test_build_index_basic(sample_chunks):
    index = build_index(sample_chunks)
    assert index.n_docs == len(sample_chunks)
    assert len(index.tfidf_vectors) == len(sample_chunks)
    assert len(index.inv_index) > 0


def test_build_index_empty():
    index = build_index([])
    assert index.n_docs == 0
    assert index.chunks == []
    assert index.tfidf_vectors == []


def test_build_index_chunk_order_preserved(sample_chunks):
    index = build_index(sample_chunks)
    for i, (chunk, expected) in enumerate(zip(index.chunks, sample_chunks)):
        assert chunk.chunk_id == expected.chunk_id


# ── Tests: query_index ────────────────────────────────────────────────────────

def test_query_index_finds_relevant(sample_chunks):
    index = build_index(sample_chunks)
    results = query_index(index, "RAG LangChain embeddings", top_k=3)
    assert len(results) > 0
    top_chunk, top_score = results[0]
    assert "doc2" in top_chunk.chunk_id  # RAG chunk should rank first


def test_query_index_returns_scores(sample_chunks):
    index = build_index(sample_chunks)
    results = query_index(index, "Python FastAPI", top_k=5)
    for chunk, score in results:
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


def test_query_index_descending_order(sample_chunks):
    index = build_index(sample_chunks)
    results = query_index(index, "Python Docker AWS", top_k=5)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_query_index_empty_query(sample_chunks):
    index = build_index(sample_chunks)
    results = query_index(index, "")
    assert results == []


def test_query_index_empty_index():
    index = build_index([])
    results = query_index(index, "python docker")
    assert results == []


def test_query_index_no_match(sample_chunks):
    index = build_index(sample_chunks)
    # Query with completely unrelated terms
    results = query_index(index, "zzzzunknownterm9999", top_k=3)
    assert results == []


def test_query_index_top_k_respected(sample_chunks):
    index = build_index(sample_chunks)
    results = query_index(index, "python", top_k=2)
    assert len(results) <= 2


# ── Tests: save_index / load_index ───────────────────────────────────────────

def test_save_and_load_index(tmp_path, sample_chunks):
    index = build_index(sample_chunks)
    path = save_index(index, str(tmp_path))
    assert os.path.exists(path)

    loaded = load_index(str(tmp_path))
    assert loaded is not None
    assert len(loaded.chunks) == len(sample_chunks)
    assert loaded.n_docs == index.n_docs


def test_load_index_missing_dir(tmp_path):
    result = load_index(str(tmp_path / "nonexistent"))
    assert result is None


def test_load_index_preserves_chunk_data(tmp_path, sample_chunks):
    index = build_index(sample_chunks)
    save_index(index, str(tmp_path))
    loaded = load_index(str(tmp_path))

    for orig, restored in zip(index.chunks, loaded.chunks):
        assert orig.chunk_id == restored.chunk_id
        assert orig.text == restored.text
        assert orig.category == restored.category


def test_save_load_round_trip_query(tmp_path, sample_chunks):
    index = build_index(sample_chunks)
    save_index(index, str(tmp_path))
    loaded = load_index(str(tmp_path))

    orig_results = query_index(index, "RAG embeddings")
    loaded_results = query_index(loaded, "RAG embeddings")

    assert len(orig_results) == len(loaded_results)
    if orig_results:
        assert orig_results[0][0].chunk_id == loaded_results[0][0].chunk_id
