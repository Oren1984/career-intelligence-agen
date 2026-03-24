"""
document_loader.py — Load local career knowledge documents from the knowledge base.

Supports: .md, .txt, .pdf (via pypdf), .json
Returns: list of RawDocument objects with text content and metadata.

Local-only. No network calls. No cloud services.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Category mapping from folder names ───────────────────────────────────────

_FOLDER_CATEGORY_MAP: dict[str, str] = {
    "resume": "resume",
    "projects": "projects",
    "skills": "skills",
    "experience": "experience",
    "achievements": "achievements",
    "strategy": "strategy",
    "interview_prep": "interview_prep",
    "general": "general",
}

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".json"}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class RawDocument:
    """A single loaded document from the knowledge base."""
    doc_id: str                        # Unique identifier (relative path)
    file_path: str                     # Absolute path
    file_name: str                     # Basename
    category: str                      # Category inferred from folder
    extension: str                     # .md | .txt | .pdf | .json
    content: str                       # Raw text content
    metadata: dict = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.content.strip()


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_text_file(path: Path) -> str:
    """Load a .txt or .md file."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read text file %s: %s", path, exc)
        return ""


def _load_pdf_file(path: Path) -> str:
    """Load a .pdf file using pypdf (already in requirements)."""
    try:
        import pypdf  # noqa: PLC0415
        reader = pypdf.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pypdf not installed; cannot load PDF: %s", path)
        return ""
    except Exception as exc:
        logger.warning("Failed to read PDF %s: %s", path, exc)
        return ""


def _load_json_file(path: Path) -> str:
    """Load a .json file and convert to readable text."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Flatten JSON to text
        if isinstance(data, list):
            parts = []
            for item in data:
                if isinstance(item, dict):
                    parts.append(
                        " | ".join(f"{k}: {v}" for k, v in item.items())
                    )
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        elif isinstance(data, dict):
            parts = []
            for k, v in data.items():
                if isinstance(v, list):
                    parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    parts.append(f"{k}: {v}")
            return "\n".join(parts)
        else:
            return str(data)
    except Exception as exc:
        logger.warning("Failed to read JSON %s: %s", path, exc)
        return ""


def _infer_category(file_path: Path, kb_root: Path) -> str:
    """Infer document category from its folder relative to the KB root."""
    try:
        rel = file_path.relative_to(kb_root)
        parts = rel.parts
        if len(parts) >= 2:
            folder = parts[0].lower()
            return _FOLDER_CATEGORY_MAP.get(folder, folder)
    except ValueError:
        pass
    return "general"


def _make_doc_id(file_path: Path, kb_root: Path) -> str:
    """Create a stable document ID from the relative path."""
    try:
        return str(file_path.relative_to(kb_root)).replace("\\", "/")
    except ValueError:
        return file_path.name


# ── Public API ────────────────────────────────────────────────────────────────

def load_documents(kb_root: str | Path) -> list[RawDocument]:
    """
    Load all supported documents from the knowledge base root directory.

    Args:
        kb_root: Path to the knowledge base root directory.

    Returns:
        List of RawDocument objects. Empty documents are skipped with a warning.
    """
    kb_path = Path(kb_root)
    if not kb_path.exists():
        logger.warning("Knowledge base directory not found: %s", kb_path)
        return []

    documents: list[RawDocument] = []

    for file_path in sorted(kb_path.rglob("*")):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            continue
        # Skip hidden files and system files
        if file_path.name.startswith(".") or file_path.name.startswith("_"):
            continue

        # Load content based on extension
        if ext == ".pdf":
            content = _load_pdf_file(file_path)
        elif ext == ".json":
            content = _load_json_file(file_path)
        else:
            content = _load_text_file(file_path)

        if not content.strip():
            logger.debug("Skipping empty document: %s", file_path)
            continue

        doc = RawDocument(
            doc_id=_make_doc_id(file_path, kb_path),
            file_path=str(file_path),
            file_name=file_path.name,
            category=_infer_category(file_path, kb_path),
            extension=ext,
            content=content,
            metadata={
                "file_size_bytes": file_path.stat().st_size,
                "last_modified": file_path.stat().st_mtime,
            },
        )
        documents.append(doc)
        logger.debug("Loaded document: %s (%s chars)", doc.doc_id, len(doc.content))

    logger.info("Loaded %d documents from %s", len(documents), kb_path)
    return documents
