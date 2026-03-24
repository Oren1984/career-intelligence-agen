"""
chunker.py — Split loaded documents into retrievable chunks with metadata.

Strategy:
- Split by paragraph (blank line separator) first
- If a paragraph exceeds max_chars, split further by sentence
- Each chunk carries: doc_id, category, file_name, chunk_index, text

No external dependencies required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.rag.document_loader import RawDocument


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class DocumentChunk:
    """A single retrievable chunk of a knowledge document."""
    chunk_id: str          # Unique: "{doc_id}::chunk{index}"
    doc_id: str            # Source document ID
    file_name: str         # Source file name
    category: str          # Document category
    text: str              # Chunk text content
    chunk_index: int       # Position within document
    metadata: dict = field(default_factory=dict)

    def is_useful(self, min_chars: int = 40) -> bool:
        """Filter out trivially short chunks."""
        return len(self.text.strip()) >= min_chars


# ── Splitting utilities ───────────────────────────────────────────────────────

_SENTENCE_SEP = re.compile(r'(?<=[.!?])\s+')
_HEADER_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_by_paragraph(text: str) -> list[str]:
    """Split text by one or more blank lines."""
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


def _split_by_sentence(text: str, max_chars: int) -> list[str]:
    """Split a long paragraph into sentence groups of at most max_chars."""
    sentences = _SENTENCE_SEP.split(text)
    groups: list[str] = []
    current: list[str] = []
    current_len = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if current_len + len(sent) > max_chars and current:
            groups.append(" ".join(current))
            current = [sent]
            current_len = len(sent)
        else:
            current.append(sent)
            current_len += len(sent) + 1

    if current:
        groups.append(" ".join(current))

    return groups


def _chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """
    Chunk text into segments.

    First tries paragraph splits. If any paragraph exceeds max_chars, splits
    further by sentence. Adds a small overlap between adjacent chunks.
    """
    paragraphs = _split_by_paragraph(text)
    raw_chunks: list[str] = []

    for para in paragraphs:
        if len(para) <= max_chars:
            raw_chunks.append(para)
        else:
            raw_chunks.extend(_split_by_sentence(para, max_chars))

    if not raw_chunks:
        return []

    # Apply overlap: each chunk starts with the tail of the previous chunk
    if overlap_chars <= 0 or len(raw_chunks) <= 1:
        return raw_chunks

    result: list[str] = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prev_tail = raw_chunks[i - 1][-overlap_chars:]
        result.append(prev_tail + " " + raw_chunks[i])

    return result


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_documents(
    documents: list[RawDocument],
    max_chars: int = 800,
    overlap_chars: int = 80,
    min_chars: int = 40,
) -> list[DocumentChunk]:
    """
    Split a list of RawDocuments into DocumentChunks.

    Args:
        documents:    Documents to chunk.
        max_chars:    Maximum characters per chunk.
        overlap_chars: Characters of context overlap between adjacent chunks.
        min_chars:    Minimum characters for a chunk to be kept.

    Returns:
        Flat list of DocumentChunk objects.
    """
    all_chunks: list[DocumentChunk] = []

    for doc in documents:
        texts = _chunk_text(doc.content, max_chars=max_chars, overlap_chars=overlap_chars)

        for i, text in enumerate(texts):
            chunk = DocumentChunk(
                chunk_id=f"{doc.doc_id}::chunk{i}",
                doc_id=doc.doc_id,
                file_name=doc.file_name,
                category=doc.category,
                text=text.strip(),
                chunk_index=i,
                metadata={**doc.metadata, "total_chunks_in_doc": len(texts)},
            )
            if chunk.is_useful(min_chars):
                all_chunks.append(chunk)

    return all_chunks
