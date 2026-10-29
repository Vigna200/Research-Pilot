"""Grounded evidence extraction. GenAI is optional and never allowed to add unsupported facts."""
import re
from .schemas import Evidence, Paper

KEYWORDS = {"method": ("method", "model", "approach"), "dataset": ("dataset", "benchmark", "cohort"), "result": ("result", "achieve", "performance"), "limitation": ("limitation", "limited", "challenge", "future work")}

def extract_evidence(papers: list[Paper]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for paper in papers:
        for sentence in re.split(r"(?<=[.!?])\s+", paper.abstract or ""):
            lowered = sentence.lower()
            category = next((name for name, terms in KEYWORDS.items() if any(term in lowered for term in terms)), None)
            if category and len(sentence) > 25:
                # A traceability score, not a measure of paper quality or claim truth.
                score = 55 + (15 if paper.doi else 0) + (10 if paper.open_access_url else 0) + (10 if paper.verification_percent >= 70 else 0) + (10 if len(sentence) >= 80 else 0)
                evidence.append(Evidence(paper_id=paper.id, paper_title=paper.title, category=category, claim=sentence.strip(), evidence_text=sentence.strip(), source_url=paper.open_access_url or paper.url, confidence_percent=min(score, 100)))
    for paper in papers:
        matches = [item.confidence_percent for item in evidence if item.paper_id == paper.id]
        paper.evidence_count = len(matches)
        paper.evidence_confidence_percent = round(sum(matches) / len(matches)) if matches else 0
    return evidence[:40]
