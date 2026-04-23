"""
rag_job_analysis.py — Extends manual job analysis with local RAG evidence retrieval.

Wraps ManualJobAnalyzer and augments each analysis result with:
- Retrieved evidence from the local knowledge base
- Evidence-backed strengths and portfolio reasoning
- Source attribution for all retrieved content
- Confidence/coverage indicators

Local-only. No network calls. No cloud services.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.manual_job_analysis import (
    ManualJobAnalyzer,
    ManualAnalysisResult,
    parse_job_text,
)
from app.rag.knowledge_service import KnowledgeService, get_knowledge_service
from app.rag.retriever import RetrievedChunk, RetrievalResult

logger = logging.getLogger(__name__)


# ── Extended result model ─────────────────────────────────────────────────────

@dataclass
class RAGAnalysisResult:
    """
    Full job analysis result augmented with local RAG evidence.

    Extends ManualAnalysisResult by adding retrieved evidence sections.
    """

    # All fields from ManualAnalysisResult
    base_result: ManualAnalysisResult

    # RAG augmentation fields
    retrieved_evidence: list[RetrievedChunk] = field(default_factory=list)
    evidence_context: str = ""           # Formatted context string for display
    evidence_used: bool = False          # Whether evidence was retrieved
    kb_size: int = 0                     # Total chunks in knowledge base
    coverage: str = "none"               # high | medium | low | none

    # Evidence-specific highlights
    project_evidence: list[RetrievedChunk] = field(default_factory=list)
    skill_evidence: list[RetrievedChunk] = field(default_factory=list)
    experience_evidence: list[RetrievedChunk] = field(default_factory=list)
    missing_evidence_notes: list[str] = field(default_factory=list)

    # Passthrough properties for convenience
    @property
    def overall_fit_score(self) -> float:
        return self.base_result.overall_fit_score

    @property
    def recommendation_label(self) -> str:
        return self.base_result.recommendation_label

    @property
    def apply_decision(self) -> str:
        return self.base_result.apply_decision

    @property
    def apply_explanation(self) -> str:
        return self.base_result.apply_explanation

    @property
    def strengths(self) -> list[str]:
        return self.base_result.strengths

    @property
    def gaps(self) -> list[str]:
        return self.base_result.gaps

    @property
    def risks(self) -> list[str]:
        return self.base_result.risks

    @property
    def action_items(self) -> list[str]:
        return self.base_result.action_items

    @property
    def best_matching_project(self) -> str:
        return self.base_result.best_matching_project

    @property
    def score_breakdown(self) -> dict[str, float]:
        return self.base_result.score_breakdown

    @property
    def parsed_job(self):
        return self.base_result.parsed_job

    def to_dict(self) -> dict[str, Any]:
        base = self.base_result.to_dict()
        base["rag"] = {
            "evidence_used": self.evidence_used,
            "kb_size": self.kb_size,
            "coverage": self.coverage,
            "evidence_context": self.evidence_context,
            "retrieved_evidence": [c.to_dict() for c in self.retrieved_evidence],
            "project_evidence": [c.to_dict() for c in self.project_evidence],
            "skill_evidence": [c.to_dict() for c in self.skill_evidence],
            "experience_evidence": [c.to_dict() for c in self.experience_evidence],
            "missing_evidence_notes": self.missing_evidence_notes,
        }
        return base


# ── Evidence classification ───────────────────────────────────────────────────

def _classify_evidence(
    chunks: list[RetrievedChunk],
) -> tuple[list[RetrievedChunk], list[RetrievedChunk], list[RetrievedChunk]]:
    """
    Split retrieved chunks into project / skill / experience buckets.
    Returns: (project_evidence, skill_evidence, experience_evidence)
    """
    project = [c for c in chunks if c.category in ("projects",)]
    skill = [c for c in chunks if c.category in ("skills",)]
    experience = [c for c in chunks if c.category in ("experience", "resume", "achievements")]
    return project, skill, experience


def _assess_coverage(chunks: list[RetrievedChunk]) -> str:
    """Rate evidence coverage as high / medium / low / none."""
    if not chunks:
        return "none"
    top_score = chunks[0].score if chunks else 0.0
    n = len(chunks)
    if top_score >= 0.12 and n >= 4:
        return "high"
    if top_score >= 0.05 and n >= 2:
        return "medium"
    if chunks:
        return "low"
    return "none"


def _identify_missing_evidence(
    gaps: list[str],
    chunks: list[RetrievedChunk],
) -> list[str]:
    """
    Check which identified gaps have no supporting evidence in the KB.
    Returns a list of notes about missing evidence.
    """
    if not gaps:
        return []

    chunk_text = " ".join(c.text.lower() for c in chunks)
    missing = []

    for gap in gaps[:5]:  # Check top 5 gaps
        gap_lower = gap.lower()
        # Simple check: any term from the gap appears in retrieved chunks?
        terms = [t for t in gap_lower.split() if len(t) > 3]
        found = any(t in chunk_text for t in terms)
        if not found:
            missing.append(
                f"No evidence for '{gap}' found in knowledge base — "
                "consider adding relevant project/experience notes."
            )

    return missing


# ── RAG Job Analyzer ──────────────────────────────────────────────────────────

class RAGJobAnalyzer:
    """
    Job analyzer that augments the standard pipeline with local RAG evidence.

    Usage:
        analyzer = RAGJobAnalyzer(profile=profile_dict)
        result = analyzer.analyze(job_text)
        print(result.evidence_context)
        print(result.coverage)
    """

    def __init__(
        self,
        profile: dict[str, Any] | None = None,
        knowledge_service: Optional[KnowledgeService] = None,
    ):
        self._profile = profile or {}
        self._ks = knowledge_service or get_knowledge_service()
        self._base_analyzer = ManualJobAnalyzer(profile=self._profile)

    def analyze(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
        top_k: int = 8,
    ) -> RAGAnalysisResult:
        """
        Full RAG-augmented job analysis.

        Flow:
        1. Parse job description
        2. Retrieve relevant local evidence
        3. Run standard scoring pipeline
        4. Augment result with evidence

        Args:
            raw_text:  Job description text.
            title:     Optional job title.
            company:   Optional company name.
            location:  Optional location.
            top_k:     Number of evidence chunks to retrieve.

        Returns:
            RAGAnalysisResult with both standard scores and retrieved evidence.
        """
        # Step 1: Run base analysis (scoring, gaps, portfolio, etc.)
        base = self._base_analyzer.analyze(
            raw_text=raw_text,
            title=title,
            company=company,
            location=location,
        )

        result = RAGAnalysisResult(base_result=base)

        # Step 2: Retrieve evidence from local knowledge base
        if not self._ks.is_ready():
            logger.info(
                "Knowledge base not indexed. "
                "Run: python scripts/ingest_knowledge.py"
            )
            result.missing_evidence_notes = [
                "Knowledge base is not ingested. "
                "Run 'python scripts/ingest_knowledge.py' to enable RAG evidence."
            ]
            return result

        try:
            retrieval = self._ks.retrieve_for_job(raw_text, top_k=top_k)

            result.retrieved_evidence = retrieval.chunks
            result.evidence_used = retrieval.has_evidence()
            result.kb_size = retrieval.kb_size
            result.coverage = _assess_coverage(retrieval.chunks)
            result.evidence_context = retrieval.as_context_string(max_chunks=5)

            # Classify evidence by type
            proj_ev, skill_ev, exp_ev = _classify_evidence(retrieval.chunks)
            result.project_evidence = proj_ev
            result.skill_evidence = skill_ev
            result.experience_evidence = exp_ev

            # Identify gaps without evidence
            result.missing_evidence_notes = _identify_missing_evidence(
                base.gaps, retrieval.chunks
            )

            logger.info(
                "RAG evidence: %d chunks retrieved (coverage: %s)",
                len(retrieval.chunks), result.coverage,
            )

        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            result.missing_evidence_notes = [f"Evidence retrieval failed: {exc}"]

        return result

    def analyze_apply_only(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """Quick apply decision with RAG evidence note."""
        result = self.analyze(raw_text, title=title, company=company, location=location)
        out = {
            "apply_decision": result.apply_decision,
            "apply_explanation": result.apply_explanation,
            "recommendation_label": result.recommendation_label,
            "overall_fit_score": result.overall_fit_score,
            "top_actions": result.action_items[:2],
            "evidence_used": result.evidence_used,
            "coverage": result.coverage,
        }
        return out

    def analyze_portfolio_only(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """Portfolio matching with RAG evidence."""
        out = self._base_analyzer.analyze_portfolio_only(
            raw_text, title=title, company=company, location=location
        )
        # Augment with project evidence if available
        if self._ks.is_ready():
            try:
                retrieval = self._ks.retrieve(raw_text[:500], top_k=3, categories=["projects"])
                out["project_evidence"] = [c.to_dict() for c in retrieval.chunks]
            except Exception:
                pass
        return out

    def analyze_rag_only(
        self,
        raw_text: str,
        title: str = "",
        company: str = "",
        location: str = "",
        top_k: int = 8,
    ) -> "RAGOnlyResult":
        """
        Retrieval-only analysis: knowledge evidence without career scoring.

        Use this in RAG Only execution mode to retrieve relevant knowledge
        base chunks for a job description without running the scoring pipeline.
        """
        result = RAGOnlyResult(raw_text=raw_text)

        if not self._ks.is_ready():
            result.missing_evidence_notes = [
                "Knowledge base is not indexed. "
                "Go to the Knowledge Base tab and click 'Ingest Knowledge Base'."
            ]
            return result

        try:
            retrieval = self._ks.retrieve_for_job(raw_text, top_k=top_k)
            result.retrieved_evidence = retrieval.chunks
            result.evidence_used = retrieval.has_evidence()
            result.kb_size = retrieval.kb_size
            result.coverage = _assess_coverage(retrieval.chunks)
            result.evidence_context = retrieval.as_context_string(max_chunks=5)
            proj_ev, skill_ev, exp_ev = _classify_evidence(retrieval.chunks)
            result.project_evidence = proj_ev
            result.skill_evidence = skill_ev
            result.experience_evidence = exp_ev
            logger.info(
                "RAG Only: %d chunks retrieved (coverage: %s)",
                len(retrieval.chunks), result.coverage,
            )
        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            result.missing_evidence_notes = [f"Evidence retrieval failed: {exc}"]

        return result

    def analyze_with_mode(
        self,
        raw_text: str,
        mode: str = "hybrid",
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> "RAGOnlyResult | RAGAnalysisResult | Any":
        """
        Dispatch analysis based on execution mode.

        Args:
            raw_text: Job description text.
            mode: One of "hybrid" | "agent_only" | "rag_only".
            title, company, location: Optional metadata overrides.

        Returns:
            RAGOnlyResult       — for rag_only mode (retrieval, no scoring)
            ManualAnalysisResult — for agent_only mode (scoring, no RAG)
            RAGAnalysisResult   — for hybrid mode (scoring + RAG evidence)
        """
        if mode == "rag_only":
            return self.analyze_rag_only(
                raw_text, title=title, company=company, location=location
            )
        if mode == "agent_only":
            return self._base_analyzer.analyze(
                raw_text, title=title, company=company, location=location
            )
        return self.analyze(raw_text, title=title, company=company, location=location)


# ── RAG-Only result model ─────────────────────────────────────────────────────

@dataclass
class RAGOnlyResult:
    """
    Result of RAG Only execution mode.

    Contains knowledge retrieval results without career scoring.
    Use when execution_mode == "rag_only".
    """
    raw_text: str
    retrieved_evidence: list[RetrievedChunk] = field(default_factory=list)
    project_evidence: list[RetrievedChunk] = field(default_factory=list)
    skill_evidence: list[RetrievedChunk] = field(default_factory=list)
    experience_evidence: list[RetrievedChunk] = field(default_factory=list)
    coverage: str = "none"
    kb_size: int = 0
    evidence_used: bool = False
    missing_evidence_notes: list[str] = field(default_factory=list)
    evidence_context: str = ""
    execution_mode: str = "rag_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_mode": self.execution_mode,
            "evidence_used": self.evidence_used,
            "kb_size": self.kb_size,
            "coverage": self.coverage,
            "retrieved_evidence": [c.to_dict() for c in self.retrieved_evidence],
            "project_evidence": [c.to_dict() for c in self.project_evidence],
            "skill_evidence": [c.to_dict() for c in self.skill_evidence],
            "experience_evidence": [c.to_dict() for c in self.experience_evidence],
            "missing_evidence_notes": self.missing_evidence_notes,
        }
