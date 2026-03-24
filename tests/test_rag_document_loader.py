"""
Tests for app.rag.document_loader

Covers: file loading, category inference, metadata extraction, edge cases.
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.rag.document_loader import (
    load_documents,
    _infer_category,
    _make_doc_id,
    _load_text_file,
    _load_json_file,
    RawDocument,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_kb(tmp_path):
    """Create a temporary knowledge base with sample files."""
    (tmp_path / "resume").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "skills").mkdir()

    (tmp_path / "resume" / "cv.md").write_text(
        "# My Resume\n\nExperienced AI Engineer with Python, FastAPI, Docker.",
        encoding="utf-8",
    )
    (tmp_path / "projects" / "rag_bot.txt").write_text(
        "RAG-powered chatbot using LangChain and ChromaDB.",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "skills.json").write_text(
        '{"python": ["FastAPI", "Pydantic"], "cloud": ["AWS", "Docker"]}',
        encoding="utf-8",
    )
    return tmp_path


# ── Tests: load_documents ─────────────────────────────────────────────────────

def test_load_documents_basic(sample_kb):
    docs = load_documents(sample_kb)
    assert len(docs) == 3
    doc_ids = {d.doc_id for d in docs}
    assert any("cv.md" in did for did in doc_ids)
    assert any("rag_bot.txt" in did for did in doc_ids)
    assert any("skills.json" in did for did in doc_ids)


def test_load_documents_categories(sample_kb):
    docs = load_documents(sample_kb)
    cats = {d.category for d in docs}
    assert "resume" in cats
    assert "projects" in cats
    assert "skills" in cats


def test_load_documents_content_not_empty(sample_kb):
    docs = load_documents(sample_kb)
    for doc in docs:
        assert doc.content.strip(), f"Document {doc.doc_id} has empty content"


def test_load_documents_nonexistent_dir():
    docs = load_documents("/nonexistent/path/xyz")
    assert docs == []


def test_load_documents_empty_dir(tmp_path):
    docs = load_documents(tmp_path)
    assert docs == []


def test_load_documents_skips_hidden_files(tmp_path):
    (tmp_path / ".hidden.md").write_text("hidden content")
    (tmp_path / "visible.md").write_text("visible content")
    docs = load_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0].file_name == "visible.md"


def test_load_documents_skips_unsupported_extensions(tmp_path):
    (tmp_path / "doc.html").write_text("<html>content</html>")
    (tmp_path / "doc.md").write_text("# Valid doc")
    docs = load_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0].extension == ".md"


def test_load_documents_json_converted_to_text(sample_kb):
    docs = load_documents(sample_kb)
    json_doc = next(d for d in docs if d.extension == ".json")
    assert "FastAPI" in json_doc.content or "python" in json_doc.content.lower()


# ── Tests: _infer_category ────────────────────────────────────────────────────

def test_infer_category_from_folder(tmp_path):
    (tmp_path / "projects" / "foo.md").parent.mkdir()
    file_path = tmp_path / "projects" / "foo.md"
    file_path.touch()
    cat = _infer_category(file_path, tmp_path)
    assert cat == "projects"


def test_infer_category_root_file(tmp_path):
    file_path = tmp_path / "notes.md"
    file_path.touch()
    cat = _infer_category(file_path, tmp_path)
    assert cat == "general"


# ── Tests: _make_doc_id ───────────────────────────────────────────────────────

def test_make_doc_id_relative(tmp_path):
    file_path = tmp_path / "resume" / "cv.md"
    doc_id = _make_doc_id(file_path, tmp_path)
    assert doc_id == "resume/cv.md"


# ── Tests: _load_text_file ────────────────────────────────────────────────────

def test_load_text_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello world", encoding="utf-8")
    result = _load_text_file(f)
    assert result == "Hello world"


def test_load_text_file_missing(tmp_path):
    result = _load_text_file(tmp_path / "nonexistent.txt")
    assert result == ""


# ── Tests: _load_json_file ────────────────────────────────────────────────────

def test_load_json_file_dict(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"skills": ["Python", "Docker"], "level": "mid"}', encoding="utf-8")
    result = _load_json_file(f)
    assert "Python" in result
    assert "Docker" in result


def test_load_json_file_list(tmp_path):
    f = tmp_path / "projects.json"
    f.write_text('[{"name": "RAG Bot", "tech": "LangChain"}]', encoding="utf-8")
    result = _load_json_file(f)
    assert "RAG Bot" in result


def test_load_json_file_invalid(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not valid json {{", encoding="utf-8")
    result = _load_json_file(f)
    assert result == ""


# ── Tests: RawDocument ────────────────────────────────────────────────────────

def test_raw_document_is_empty():
    doc = RawDocument(
        doc_id="test", file_path="", file_name="test.md",
        category="general", extension=".md", content="",
    )
    assert doc.is_empty()


def test_raw_document_not_empty():
    doc = RawDocument(
        doc_id="test", file_path="", file_name="test.md",
        category="general", extension=".md", content="Some content",
    )
    assert not doc.is_empty()
