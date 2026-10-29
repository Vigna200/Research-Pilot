"""Metadata verification and citation rendering. Scores are system signals, never paper quality claims."""
import asyncio
import re
import httpx
from .config import settings
from .schemas import Paper, SourceStatus


def _crossref_authors(message: dict) -> list[str]:
    return [" ".join(x for x in (author.get("given"), author.get("family")) if x) for author in message.get("author", [])]


def _publication_type(work_type: str | None, venue: str | None) -> str:
    mapping = {"journal-article": "Journal Article", "proceedings-article": "Conference / Proceedings Paper", "posted-content": "Preprint", "book-chapter": "Book Chapter", "dataset": "Dataset", "dissertation": "Thesis / Dissertation"}
    result = mapping.get(work_type or "", "Other")
    if venue and "arxiv" in venue.lower(): return "Preprint"
    return result


def _year(message: dict) -> int | None:
    for key in ("published-print", "published-online", "issued"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0]: return parts[0][0]
    return None


def ieee_citation(paper: Paper) -> str:
    authors = paper.authors[:6]
    rendered = []
    for author in authors:
        parts = author.split()
        rendered.append(f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else author)
    author_text = ", ".join(rendered) + (", et al." if len(paper.authors) > 6 else "")
    fields = [author_text, f'“{paper.title},“']
    if paper.venue: fields.append(paper.venue)
    if paper.year: fields.append(str(paper.year))
    if paper.doi: fields.append(f"doi: {paper.doi}")
    return ", ".join(field for field in fields if field).rstrip(",") + "."


def _score(paper: Paper, crossref_match: bool) -> None:
    checks: list[str] = []
    score = 0
    if paper.doi:
        score += 20; checks.append("DOI available")
    if crossref_match:
        score += 25; checks.append("Crossref metadata matched")
    if "semantic_scholar" in paper.sources:
        score += 15; checks.append("Semantic Scholar record")
    if "openalex" in paper.sources:
        score += 15; checks.append("OpenAlex record")
    if paper.venue:
        score += 10; checks.append("Venue identified")
    if paper.authors:
        score += 5; checks.append("Authors identified")
    if paper.abstract:
        score += 5; checks.append("Abstract available")
    if paper.open_access_url:
        score += 5; checks.append("Open-access link available")
    paper.verification_percent = min(score, 100)
    paper.verification_checks = checks
    paper.ieee_citation = ieee_citation(paper)


async def _enrich_from_crossref(client: httpx.AsyncClient, paper: Paper) -> bool:
    if not paper.doi: return False
    response = await client.get(f"https://api.crossref.org/works/{paper.doi}")
    response.raise_for_status()
    message = response.json().get("message", {})
    returned_doi = (message.get("DOI") or "").lower()
    if returned_doi != paper.doi.lower(): return False
    paper.sources = sorted(set(paper.sources + ["crossref"]))
    paper.publisher = message.get("publisher") or paper.publisher
    paper.issn = message.get("ISSN") or paper.issn
    paper.venue = (message.get("container-title") or [paper.venue])[0] or paper.venue
    paper.publication_type = _publication_type(message.get("type"), paper.venue)
    paper.year = _year(message) or paper.year
    paper.authors = _crossref_authors(message) or paper.authors
    paper.abstract = paper.abstract or message.get("abstract")
    paper.url = message.get("URL") or paper.url
    return True


async def verify_papers(papers: list[Paper]) -> SourceStatus:
    successes = 0
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        for paper in papers:
            matched = False
            try:
                matched = await _enrich_from_crossref(client, paper)
                successes += int(matched)
            except httpx.HTTPError:
                pass
            _score(paper, matched)
    return SourceStatus(source="crossref_verification", succeeded=True, count=successes)
