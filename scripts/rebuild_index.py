"""
rebuild_index.py — Force a full rebuild of the local knowledge index.

Use this after adding, editing, or removing documents from the knowledge base.

Usage:
    python scripts/rebuild_index.py
    python scripts/rebuild_index.py --kb-root /path/to/knowledge_base
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Force rebuild of the local knowledge index."
    )
    parser.add_argument("--kb-root", default=None)
    args = parser.parse_args()

    try:
        from app.rag.knowledge_service import KnowledgeService
    except ImportError as exc:
        print(f"Import failed: {exc}")
        return 1

    kb_root = args.kb_root or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge_base",
    )

    ks = KnowledgeService(kb_root=kb_root)
    status = ks.rebuild()

    if status.is_indexed:
        print(f"Index rebuilt: {status.total_documents} docs, {status.total_chunks} chunks")
        return 0
    else:
        print("No documents found to index.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
