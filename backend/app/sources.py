import asyncio
from collections.abc import Iterable
import hashlib
from difflib import SequenceMatcher
import httpx
from .config import settings
from .schemas import Paper, SourceStatus


class ScholarlySource:
    name: str
    async def search(self, query: str, limit: int) -> list[Paper]:
        raise NotImplementedError


class SemanticScholarSource(ScholarlySource):
    name = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, limit: int) -> list[Paper]:
        headers = {"x-api-key": settings.semantic_scholar_api_key} if settings.semantic_scholar_api_key else {}
        params = {"query": query, "limit": limit, "fields": "paperId,title,abstract,authors,year,venue,externalIds,citationCount,openAccessPdf,url"}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(self.endpoint, params=params, headers=headers)
            response.raise_for_status()
        papers = []
        for item in response.json().get("data", []):
            ids, oa = item.get("externalIds") or {}, item.get("openAccessPdf") or {}
            papers.append(Paper(
                id=f"s2:{item['paperId']}", title=item.get("title") or "Untitled",
                abstract=item.get("abstract"), authors=[a.get("name", "") for a in item.get("authors", [])],
                year=item.get("year"), venue=item.get("venue"), doi=ids.get("DOI"), url=item.get("url"),
                semantic_scholar_id=item.get("paperId"), citation_count=item.get("citationCount") or 0,
                open_access=bool(oa.get("url")), open_access_url=oa.get("url"), sources=[self.name],
            ))
        return papers


class OpenAlexSource(ScholarlySource):
    name = "openalex"
    endpoint = "https://api.openalex.org/works"

    async def search(self, query: str, limit: int) -> list[Paper]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(self.endpoint, params={"search": query, "per-page": limit})
            response.raise_for_status()
        papers = []
        for item in response.json().get("results", []):
            abstract_index = item.get("abstract_inverted_index") or {}
            if abstract_index:
                ordered_words = [""] * (max(position for positions in abstract_index.values() for position in positions) + 1)
                for word, positions in abstract_index.items():
                    for position in positions: ordered_words[position] = word
                abstract = " ".join(ordered_words)
            else:
                abstract = None
            doi = (item.get("doi") or "").removeprefix("https://doi.org/") or None
            oa = item.get("open_access") or {}
            papers.append(Paper(
                id=f"oa:{item['id'].rsplit('/', 1)[-1]}", title=item.get("title") or "Untitled",
                abstract=abstract, authors=[a["author"].get("display_name", "") for a in item.get("authorships", [])],
                year=item.get("publication_year"), venue=(item.get("primary_location") or {}).get("source", {}).get("display_name") if (item.get("primary_location") or {}).get("source") else None,
                doi=doi, url=item.get("doi") or item.get("id"), citation_count=item.get("cited_by_count") or 0,
                open_access=bool(oa.get("is_oa")), open_access_url=oa.get("oa_url"), sources=[self.name],
            ))
        return papers


class CrossrefSource(ScholarlySource):
    name = "crossref"
    endpoint = "https://api.crossref.org/works"

    async def search(self, query: str, limit: int) -> list[Paper]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(self.endpoint, params={"query.bibliographic": query, "rows": limit, "select": "DOI,title,author,published,container-title,publisher,type,ISSN,URL"})
            response.raise_for_status()
        papers = []
        for item in response.json().get("message", {}).get("items", []):
            date_parts = (item.get("published") or {}).get("date-parts") or []
            papers.append(Paper(id=f"cr:{item.get('DOI', '')}", title=(item.get("title") or ["Untitled"])[0], authors=[" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in item.get("author", [])], year=date_parts[0][0] if date_parts and date_parts[0] else None, venue=(item.get("container-title") or [None])[0], publisher=item.get("publisher"), issn=item.get("ISSN") or [], publication_type={"journal-article": "Journal Article", "proceedings-article": "Conference / Proceedings Paper", "posted-content": "Preprint"}.get(item.get("type"), "Other"), doi=item.get("DOI"), url=item.get("URL"), sources=[self.name]))
        return papers


def _fingerprint(paper: Paper) -> str:
    title = "".join(c.lower() for c in paper.title if c.isalnum())
    return title[:120]


def deduplicate(papers: Iterable[Paper]) -> list[Paper]:
    output: list[Paper] = []
    seen: dict[str, Paper] = {}
    for paper in papers:
        keys = [f"doi:{paper.doi.lower()}" if paper.doi else "", f"s2:{paper.semantic_scholar_id}" if paper.semantic_scholar_id else "", f"title:{_fingerprint(paper)}"]
        existing = next((seen[k] for k in keys if k and k in seen), None)
        if not existing:
            existing = next((candidate for candidate in output if paper.year == candidate.year and SequenceMatcher(None, _fingerprint(paper), _fingerprint(candidate)).ratio() >= 0.94), None)
        if existing:
            existing.sources = sorted(set(existing.sources + paper.sources))
            if not existing.abstract and paper.abstract: existing.abstract = paper.abstract
            if not existing.open_access_url and paper.open_access_url:
                existing.open_access, existing.open_access_url = True, paper.open_access_url
            existing.citation_count = max(existing.citation_count, paper.citation_count)
            existing.publisher = existing.publisher or paper.publisher
            existing.issn = existing.issn or paper.issn
            if existing.publication_type == "Other": existing.publication_type = paper.publication_type
            continue
        for key in keys:
            if key: seen[key] = paper
        output.append(paper)
    return output


async def discover(queries: list[str], per_query: int) -> tuple[list[Paper], list[SourceStatus]]:
    sources = [SemanticScholarSource(), OpenAlexSource(), CrossrefSource()]
    async def run(source: ScholarlySource):
        try:
            batches = await asyncio.gather(*(source.search(q, per_query) for q in queries))
            papers = [p for batch in batches for p in batch]
            return papers, SourceStatus(source=source.name, succeeded=True, count=len(papers))
        except (httpx.HTTPError, ValueError) as error:
            return [], SourceStatus(source=source.name, succeeded=False, error=str(error))
    results = await asyncio.gather(*(run(source) for source in sources))
    return [p for papers, _ in results for p in papers], [status for _, status in results]
