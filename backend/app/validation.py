"""Counter-evidence search; absence is never interpreted as global novelty."""
from .schemas import Paper, ResearchGap
from .sources import deduplicate, discover

def query_for_gap(question: str, gap: ResearchGap) -> str:
    if "generalization" in gap.title.lower(): return f"{question} external validation cross-dataset generalization"
    if "calibration" in gap.title.lower(): return f"{question} uncertainty calibration evaluation"
    return f"{question} reproducibility benchmark comparison"

async def validate_gaps(question: str, gaps: list[ResearchGap], initial_papers: list[Paper]) -> tuple[list[ResearchGap], list[Paper]]:
    validated: list[ResearchGap] = []
    expansion: list[Paper] = []
    initial_titles = {p.title.lower() for p in initial_papers}
    for gap in gaps:
        if not gap.status.startswith("Potential"):
            gap.status = "Actionable direction — not a novelty claim"
            continue
        query = query_for_gap(question, gap)
        found, _ = await discover([query], 5)
        candidates = deduplicate(found)
        new_titles = [p.title for p in candidates if p.title.lower() not in initial_titles]
        gap.validation_query = query
        gap.counter_evidence = new_titles[:5]
        expansion.extend(candidates)
        if new_titles and gap.status.startswith("Potential"):
            gap.status = "Counter-evidence found — refine candidate"
            gap.confidence = min(gap.confidence, 30)
            gap.statement += " Related studies were found by targeted counter-search; inspect them before treating this as a gap."
        elif gap.status.startswith("Potential"):
            gap.status = "Potential gap — no counter-evidence in searched sources"
            gap.statement += " This is limited to the stated corpus and counter-search scope, not a global novelty claim."
    return validated + gaps, deduplicate(expansion)
