"""Abstention-first corpus gap candidates. They are never claims of global novelty."""
from .schemas import Paper, ResearchGap


def analyze_gaps(question: str, papers: list[Paper]) -> list[ResearchGap]:
    evidence = [paper.title for paper in papers]
    text = " ".join(f"{paper.title} {paper.abstract or ''}" for paper in papers).lower()
    existing = "The analyzed corpus contains work on: " + "; ".join(paper.title for paper in papers[:3]) + "."
    gaps: list[ResearchGap] = []
    if "external" not in text and "cross-dataset" not in text and "generaliz" not in text:
        gaps.append(ResearchGap(title="External-dataset generalization", gap_type="Evaluation gap", statement="No explicit external or cross-dataset evaluation was identified in the titles and abstracts of the five analyzed papers.", status="Potential gap — counter-search required", confidence=48, evidence=evidence, what_exists=existing, next_step="Search for external-validation and cross-dataset studies, then evaluate the strongest baseline on an independently sourced dataset."))
    if "calibration" not in text and "uncertainty" not in text:
        gaps.append(ResearchGap(title="Reliability and calibration reporting", gap_type="Evaluation gap", statement="The five-paper corpus did not explicitly report calibration or uncertainty evaluation in its available metadata/abstract text.", status="Potential gap — counter-search required", confidence=45, evidence=evidence, what_exists=existing, next_step="Counter-search for uncertainty-aware evaluations; if evidence remains sparse, compare calibration, selective prediction, and error analysis alongside task accuracy."))
    gaps.append(ResearchGap(title="Controlled reproducibility benchmark", gap_type="Reproducibility gap", statement="The corpus contains different methods and evaluation contexts; a controlled, documented reproduction benchmark is a practical additional contribution.", status="Actionable direction", confidence=60, evidence=evidence, what_exists=existing, next_step="Reproduce the top available baselines with fixed splits, preprocessing, metrics, compute budget, and code/data provenance."))
    return gaps
