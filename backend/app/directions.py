"""Conservative research-direction templates grounded in the discovered corpus."""
from .schemas import Paper, Resource, ResearchDirection


def recommend(question: str, papers: list[Paper], resources: list[Resource]) -> list[ResearchDirection]:
    corpus = f"{question} {' '.join(p.title for p in papers)}".lower()
    datasets = [r.name for r in resources if r.kind == "dataset"]
    stack = [r.name for r in resources if r.kind == "technology"]
    baselines = [p.title for p in papers[:3]]
    evidence = [p.title for p in papers[:3]]
    domain = "medical-image" if any(x in corpus for x in ("medical", "radiology", "image")) else "target-domain"
    directions = [ResearchDirection(
        title="External-validation study",
        research_question=f"How well do leading methods for {question.rstrip('?')} generalize across independent {domain} datasets?",
        hypothesis="Performance measured on a single benchmark will decrease under an external dataset shift; targeted calibration or adaptation will reduce that gap.",
        rationale="The top retrieved corpus provides baselines to reproduce before evaluating generalization. This is a proposed direction, not a claim that no prior external-validation study exists.",
        baselines=baselines, datasets=datasets or ["Select a second, independently sourced dataset after access and licensing review"], technology_stack=stack or ["PyTorch"], metrics=["Primary task metric", "F1", "AUROC where applicable", "Calibration error"], feasibility="Medium — requires compatible datasets and consistent preprocessing.", evidence_papers=evidence,
    ), ResearchDirection(
        title="Reproducible baseline benchmark",
        research_question=f"Under one transparent evaluation protocol, which published baselines are most reliable for {question.rstrip('?')}?",
        hypothesis="A standardized split, preprocessing pipeline, and reporting protocol will expose differences not attributable to model architecture alone.",
        rationale="Use the discovered papers as a baseline shortlist and preserve exact code, data access, and metric provenance.",
        baselines=baselines, datasets=datasets or ["Use the benchmark named by the selected baseline paper"], technology_stack=stack or ["PyTorch"], metrics=["Primary task metric", "F1", "Runtime", "Parameter count", "Reproducibility checklist"], feasibility="High — begin with open-access data and repositories only.", evidence_papers=evidence,
    )]
    return directions
