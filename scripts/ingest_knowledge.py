"""
ingest_knowledge.py — Ingest local career knowledge files into the local RAG index.

Usage:
    python scripts/ingest_knowledge.py
    python scripts/ingest_knowledge.py --kb-root /path/to/knowledge_base
    python scripts/ingest_knowledge.py --rebuild

This script loads all supported files from the knowledge base folder,
chunks them, builds a TF-IDF index, and saves it locally.

All data stays local. No network calls. No cloud services.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure repo root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest local career knowledge files into the local RAG index."
    )
    parser.add_argument(
        "--kb-root",
        default=None,
        help="Path to knowledge base root (default: knowledge_base/)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild even if index already exists.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        from app.rag.knowledge_service import KnowledgeService
    except ImportError as exc:
        logger.error("Import failed: %s", exc)
        logger.error("Run from the repo root: python scripts/ingest_knowledge.py")
        return 1

    kb_root = args.kb_root or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge_base",
    )

    if not os.path.exists(kb_root):
        logger.error(
            "Knowledge base directory not found: %s\n"
            "Create it and add your .md, .txt, or .pdf career documents.",
            kb_root,
        )
        return 1

    logger.info("Knowledge base root: %s", kb_root)
    logger.info("Rebuild mode: %s", args.rebuild)
    logger.info("")

    ks = KnowledgeService(kb_root=kb_root)
    status = ks.ingest(rebuild=args.rebuild)

    if status.is_indexed:
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"  Documents:   {status.total_documents}")
        print(f"  Chunks:      {status.total_chunks}")
        print(f"  Categories:  {', '.join(status.categories) or 'none'}")
        print(f"  Indexed at:  {status.last_ingest_iso}")
        print(f"  Index dir:   {status.index_dir}")
        print("=" * 60)
        print("\nThe knowledge base is ready for RAG job analysis and Q&A.")
        print("Start the dashboard: streamlit run dashboard/streamlit_app.py")
        return 0
    else:
        print("\nIngestion complete but no documents were indexed.")
        print(
            f"Add .md, .txt, or .pdf files to: {kb_root}\n"
            "See knowledge_base/README.md for guidance."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
