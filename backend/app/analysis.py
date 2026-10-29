"""Structured, provenance-preserving abstract analysis.

This is intentionally conservative: it labels only text directly present in the
available abstract. Full-text section parsing is a later pipeline stage.
"""
import re
from .schemas import ComparisonMatrix, Paper, StructuredPaperRecord

TERMS = {
    "methods": ("transformer", "vision-language", "large language model", "llm", "cnn", "network", "model", "framework"),
    "datasets": ("dataset", "benchmark", "cohort", "mimic", "chexpert", "chestxray", "imagenet"),
    "metrics": ("accuracy", "auroc", "auc", "f1", "precision", "recall", "sensitivity", "specificity"),
    "results": ("achiev", "outperform", "performance", "result", "improv"),
    "limitations": ("limitation", "limited", "challenge", "future work", "remain", "generaliz"),
}

def _sentences(text: str, terms: tuple[str, ...]) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 25 and any(term in s.lower() for term in terms)][:3]

def structured_analysis(papers: list[Paper]) -> tuple[list[StructuredPaperRecord], list[ComparisonMatrix]]:
    records: list[StructuredPaperRecord] = []
    for paper in papers:
        abstract = paper.abstract or ""
        values = {field: _sentences(abstract, terms) for field, terms in TERMS.items()}
        records.append(StructuredPaperRecord(paper_id=paper.id, paper_title=paper.title, research_problem=_sentences(abstract, ("problem", "aim", "objective", "address"))[0] if _sentences(abstract, ("problem", "aim", "objective", "address")) else None, **values))
    matrices = []
    for dimension in ("methods", "datasets", "metrics", "limitations"):
        matrices.append(ComparisonMatrix(dimension=dimension, rows=[{"paper": r.paper_title, dimension: " | ".join(getattr(r, dimension)) or "Not stated in abstract"} for r in records]))
    return records, matrices
