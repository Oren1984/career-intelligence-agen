"""
Tests for app.rag.chunker

Covers: chunking, overlap, edge cases, metadata passing.
"""
import pytest

from app.rag.chunker import chunk_documents, _chunk_text, _split_by_paragraph, DocumentChunk
from app.rag.document_loader import RawDocument


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_doc(content: str, category: str = "general", file_name: str = "test.md") -> RawDocument:
    return RawDocument(
        doc_id=f"test/{file_name}",
        file_path=f"/kb/{file_name}",
        file_name=file_name,
        category=category,
        extension=".md",
        content=content,
    )


# ── Tests: _split_by_paragraph ────────────────────────────────────────────────

def test_split_by_paragraph_basic():
    text = "Para one.\n\nPara two.\n\nPara three."
    parts = _split_by_paragraph(text)
    assert len(parts) == 3


def test_split_by_paragraph_single():
    text = "Single paragraph with no breaks."
    parts = _split_by_paragraph(text)
    assert len(parts) == 1


def test_split_by_paragraph_empty():
    parts = _split_by_paragraph("")
    assert parts == []


def test_split_by_paragraph_strips_whitespace():
    text = "  Para one.  \n\n  Para two.  "
    parts = _split_by_paragraph(text)
    assert all(p == p.strip() for p in parts)


# ── Tests: _chunk_text ────────────────────────────────────────────────────────

def test_chunk_text_short_content():
    text = "Short content under max chars."
    chunks = _chunk_text(text, max_chars=800, overlap_chars=0)
    assert len(chunks) == 1
    assert "Short content" in chunks[0]


def test_chunk_text_long_paragraph():
    # Create a long paragraph that should be split by sentences
    sentences = [f"This is sentence number {i} which adds to the total length." for i in range(20)]
    text = " ".join(sentences)
    chunks = _chunk_text(text, max_chars=200, overlap_chars=0)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 300  # Some tolerance for overlap


def test_chunk_text_multiple_paragraphs():
    text = "Para one content here.\n\nPara two content here.\n\nPara three content here."
    chunks = _chunk_text(text, max_chars=800, overlap_chars=0)
    assert len(chunks) == 3


def test_chunk_text_overlap_adds_context():
    text = "First paragraph with useful context.\n\nSecond paragraph with different content."
    chunks = _chunk_text(text, max_chars=800, overlap_chars=20)
    # With overlap, second chunk should include tail of first
    if len(chunks) > 1:
        # Overlap chars from end of first chunk should appear in second
        first_tail = chunks[0][-20:]
        assert first_tail in chunks[1]


# ── Tests: chunk_documents ────────────────────────────────────────────────────

def test_chunk_documents_basic():
    docs = [
        _make_doc("This is a resume chunk with enough content for testing purposes here.", "resume"),
    ]
    chunks = chunk_documents(docs)
    assert len(chunks) >= 1
    assert chunks[0].category == "resume"
    assert chunks[0].doc_id == "test/test.md"


def test_chunk_documents_metadata_preserved():
    docs = [
        _make_doc("This project description has enough content to pass the minimum length filter.", "projects", "myproject.md"),
    ]
    chunks = chunk_documents(docs)
    assert chunks[0].file_name == "myproject.md"
    assert chunks[0].category == "projects"


def test_chunk_documents_chunk_ids_unique():
    docs = [
        _make_doc("Para one.\n\nPara two.\n\nPara three.", "skills"),
    ]
    chunks = chunk_documents(docs, max_chars=30, overlap_chars=0)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


def test_chunk_documents_filters_short_chunks():
    docs = [
        _make_doc("OK.\n\nThis is a substantial chunk with real content.", "general"),
    ]
    chunks = chunk_documents(docs, min_chars=20)
    for chunk in chunks:
        assert len(chunk.text) >= 20


def test_chunk_documents_empty_list():
    chunks = chunk_documents([])
    assert chunks == []


def test_chunk_documents_empty_document():
    docs = [_make_doc("")]
    chunks = chunk_documents(docs)
    assert chunks == []


def test_chunk_documents_multiple_docs():
    docs = [
        _make_doc("Resume content with Python FastAPI Docker.", "resume"),
        _make_doc("Project: RAG chatbot using LangChain and OpenAI.", "projects"),
    ]
    chunks = chunk_documents(docs)
    categories = {c.category for c in chunks}
    assert "resume" in categories
    assert "projects" in categories


def test_chunk_id_format():
    docs = [_make_doc("Content here for testing the chunk ID format.")]
    chunks = chunk_documents(docs)
    assert "::chunk" in chunks[0].chunk_id


def test_document_chunk_is_useful():
    long_chunk = DocumentChunk(
        chunk_id="x::chunk0", doc_id="x", file_name="x.md",
        category="general", text="This is a useful chunk.", chunk_index=0,
    )
    assert long_chunk.is_useful(min_chars=10)

    short_chunk = DocumentChunk(
        chunk_id="y::chunk0", doc_id="y", file_name="y.md",
        category="general", text="Hi", chunk_index=0,
    )
    assert not short_chunk.is_useful(min_chars=10)
