"""
qa_service.py — Grounded career Q&A over the local knowledge base.

Answers freeform questions about the user's career using retrieved evidence.
All answers are explicitly grounded in retrieved chunks — no hallucination.

Local-only. No network calls. No cloud services required.
Optional: LLM integration for richer synthesized answers (if configured).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.rag.knowledge_service import KnowledgeService, get_knowledge_service
from app.rag.retriever import RetrievedChunk, RetrievalResult

logger = logging.getLogger(__name__)


# ── Answer model ──────────────────────────────────────────────────────────────

@dataclass
class QAAnswer:
    """A grounded answer to a career question."""
    question: str
    answer: str                          # Synthesized answer text
    evidence: list[RetrievedChunk] = field(default_factory=list)
    confidence: str = "low"              # high | medium | low | none
    evidence_summary: str = ""           # One-line evidence overview
    sources: list[str] = field(default_factory=list)  # File references
    has_evidence: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "evidence_summary": self.evidence_summary,
            "sources": self.sources,
            "has_evidence": self.has_evidence,
            "evidence": [c.to_dict() for c in self.evidence],
        }


# ── Evidence-based answer synthesis ──────────────────────────────────────────

def _assess_confidence(retrieved: RetrievalResult, min_good_score: float = 0.05) -> str:
    """Estimate answer confidence based on retrieval quality."""
    if not retrieved.chunks:
        return "none"
    top_score = retrieved.chunks[0].score if retrieved.chunks else 0.0
    n_relevant = sum(1 for c in retrieved.chunks if c.score >= min_good_score)
    if top_score >= 0.15 and n_relevant >= 3:
        return "high"
    if top_score >= 0.07 and n_relevant >= 2:
        return "medium"
    if top_score >= 0.01:
        return "low"
    return "none"


def _synthesize_answer_from_evidence(
    question: str,
    retrieved: RetrievalResult,
) -> str:
    """
    Synthesize a grounded answer by extracting relevant sentences from evidence.

    This is a rule-based synthesizer — no LLM required.
    It extracts and presents the most relevant content from retrieved chunks.
    """
    if not retrieved.chunks:
        return (
            "No relevant evidence found in the local knowledge base for this question. "
            "Try adding more documents to knowledge_base/ and re-running ingestion."
        )

    q_lower = question.lower()

    # Build answer from top evidence chunks
    parts: list[str] = []

    # Lead with the best matching content
    for i, chunk in enumerate(retrieved.chunks[:3]):
        # Try to extract the most relevant sentences from the chunk
        sentences = [
            s.strip()
            for s in chunk.text.replace("\n", " ").split(".")
            if len(s.strip()) > 20
        ]
        if sentences:
            # Use the full chunk text (already chunked to ~800 chars)
            preview = chunk.text.strip()
            if len(preview) > 350:
                preview = preview[:350] + "…"
            parts.append(f"{preview}")

    if not parts:
        return "Evidence found but could not be extracted. Review source files directly."

    # Frame the answer
    evidence_text = "\n\n".join(parts)
    prefix = _generate_answer_prefix(question, retrieved)

    return f"{prefix}\n\n{evidence_text}"


def _generate_answer_prefix(question: str, retrieved: RetrievalResult) -> str:
    """Generate a contextual answer opener based on the question type."""
    q_lower = question.lower()
    n = len(retrieved.chunks)
    top_cat = retrieved.chunks[0].category if retrieved.chunks else "general"

    if any(w in q_lower for w in ["which project", "best project", "what project"]):
        return f"Based on {n} piece(s) of evidence from your knowledge base:"
    if any(w in q_lower for w in ["skill", "experience", "evidence", "background"]):
        return f"Here is what your knowledge base shows ({n} relevant section(s)):"
    if any(w in q_lower for w in ["gap", "missing", "lack", "weak"]):
        return f"Reviewing your knowledge base ({n} relevant section(s)):"
    if any(w in q_lower for w in ["role", "position", "job", "align"]):
        return f"From your career materials ({n} relevant section(s)):"
    return f"Drawing from {n} relevant section(s) in your knowledge base:"


# ── QA Service ────────────────────────────────────────────────────────────────

class CareerQAService:
    """
    Answers career questions grounded in the local knowledge base.

    All answers are evidence-backed. When evidence is weak, the answer
    explicitly says so rather than hallucinating.

    Usage:
        qa = CareerQAService()
        answer = qa.ask("Which of my projects best demonstrates RAG?")
        print(answer.answer)
        for chunk in answer.evidence:
            print(chunk.short_summary())
    """

    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        top_k: int = 5,
    ):
        self._ks = knowledge_service or get_knowledge_service()
        self._top_k = top_k

    def ask(
        self,
        question: str,
        categories: list[str] | None = None,
        top_k: int | None = None,
    ) -> QAAnswer:
        """
        Answer a career question using retrieved evidence.

        Args:
            question: Natural language question about the user's career.
            categories: Optional filter — only search in these categories.
            top_k: Override default number of evidence chunks.

        Returns:
            QAAnswer with grounded answer, evidence, and confidence rating.
        """
        if not question.strip():
            return QAAnswer(
                question=question,
                answer="Please provide a question.",
                confidence="none",
            )

        if not self._ks.is_ready():
            return QAAnswer(
                question=question,
                answer=(
                    "The knowledge base has not been ingested yet. "
                    "Run: python scripts/ingest_knowledge.py"
                ),
                confidence="none",
                has_evidence=False,
            )

        retrieved = self._ks.retrieve(
            query=question,
            top_k=top_k or self._top_k,
            categories=categories,
        )

        confidence = _assess_confidence(retrieved)
        answer_text = _synthesize_answer_from_evidence(question, retrieved)
        sources = list({c.file_name for c in retrieved.chunks})

        # Build evidence summary
        if retrieved.chunks:
            top = retrieved.chunks[0]
            evidence_summary = (
                f"Top match: {top.category}/{top.file_name} "
                f"(score: {top.score:.3f})"
            )
        else:
            evidence_summary = "No evidence retrieved."

        return QAAnswer(
            question=question,
            answer=answer_text,
            evidence=retrieved.chunks,
            confidence=confidence,
            evidence_summary=evidence_summary,
            sources=sources,
            has_evidence=retrieved.has_evidence(),
        )

    def ask_batch(self, questions: list[str]) -> list[QAAnswer]:
        """Answer multiple questions."""
        return [self.ask(q) for q in questions]

    def summarize_skills(self, skill_name: str) -> QAAnswer:
        """Find all evidence for a specific skill."""
        return self.ask(
            f"What evidence do I have for {skill_name}? "
            f"What projects or experience demonstrate {skill_name}?"
        )

    def find_best_project_for_role(self, role: str) -> QAAnswer:
        """Find the best matching project for a given role."""
        return self.ask(
            f"Which of my projects best supports a {role} role? "
            f"What evidence do I have that is relevant to {role}?"
        )

    def identify_recurring_gaps(self) -> QAAnswer:
        """Look for skill gaps mentioned in job analysis notes."""
        return self.ask(
            "What skill gaps or missing skills appear in my notes? "
            "What areas do I need to improve based on my career materials?",
            categories=["strategy", "interview_prep", "general"],
        )
