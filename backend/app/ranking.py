import math
import re
from datetime import datetime
from .schemas import Paper


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9-]{3,}", text.lower()))


def rank_papers(papers: list[Paper], question: str) -> list[Paper]:
    query_terms = _tokens(question)
    max_citations = max((math.log1p(p.citation_count) for p in papers), default=1) or 1
    year_now = datetime.now().year
    for paper in papers:
        title_overlap = len(query_terms & _tokens(paper.title)) / max(len(query_terms), 1)
        abstract_overlap = len(query_terms & _tokens(paper.abstract or "")) / max(len(query_terms), 1)
        relevance = min(1.0, (2 * title_overlap + abstract_overlap) / 3)
        impact = math.log1p(paper.citation_count) / max_citations
        recency = max(0.0, 1 - ((year_now - (paper.year or 2000)) / 20))
        paper.ranking_score = round(0.65 * relevance + 0.2 * impact + 0.15 * recency, 4)
        paper.similarity_percent = round(relevance * 100)
        paper.ranking_reasons = [
            f"lexical relevance {relevance:.2f}",
            f"citation signal {impact:.2f}",
            f"recency signal {recency:.2f}",
        ]
    return sorted(papers, key=lambda p: p.ranking_score, reverse=True)
