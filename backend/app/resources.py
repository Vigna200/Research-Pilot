"""Resource discovery only returns records supplied by official APIs or known official dataset pages."""
import re
import httpx
from .config import settings
from .schemas import Paper, Resource, SourceStatus

DATASETS = {
    "mimic-cxr": ("MIMIC-CXR", "https://physionet.org/content/mimic-cxr/", "PhysioNet dataset for chest radiographs and reports; credentialed access applies."),
    "chexpert": ("CheXpert", "https://stanfordmlgroup.github.io/competitions/chexpert/", "Stanford chest-radiograph benchmark for uncertainty-aware classification."),
    "chestxray14": ("NIH ChestX-ray14", "https://nihcc.app.box.com/v/ChestXray-NIHCC", "NIH chest X-ray image collection."),
    "brats": ("BraTS", "https://www.synapse.org/Synapse:syn51156910/wiki/622351", "Brain tumour segmentation benchmark."),
    "tcia": ("The Cancer Imaging Archive", "https://www.cancerimagingarchive.net/", "Open cancer-imaging data collections."),
    "imagenet": ("ImageNet", "https://www.image-net.org/", "Large-scale visual-recognition dataset."),
}


def dataset_candidates(papers: list[Paper]) -> list[Resource]:
    matches: dict[str, Paper] = {}
    for paper in papers:
        text = f"{paper.title} {paper.abstract or ''}".lower()
        for token in DATASETS:
            if token in text and token not in matches:
                matches[token] = paper
    resources = []
    for token, paper in matches.items():
        name, url, description = DATASETS[token]
        resources.append(Resource(name=name, kind="dataset", url=url, verified=True, official=True, description=description, relevance="Mentioned in the retrieved paper corpus; assess its access terms and task fit before use.", evidence=f"Mentioned by: {paper.title}"))
    return resources


def technology_candidates(question: str, papers: list[Paper]) -> list[Resource]:
    corpus = f"{question} {' '.join(p.title + ' ' + (p.abstract or '') for p in papers)}".lower()
    tech: list[Resource] = []
    if any(term in corpus for term in ("image", "radiology", "medical", "vision")):
        tech.extend([
            Resource(name="PyTorch", kind="technology", url="https://pytorch.org/", verified=True, official=True, description="Deep-learning framework.", relevance="Suitable for reproducing and extending vision or multimodal baselines."),
            Resource(name="MONAI", kind="technology", url="https://monai.io/", verified=True, official=True, description="PyTorch-native framework for medical imaging.", relevance="Useful when the retrieved topic involves medical-image preprocessing, training, or evaluation."),
        ])
    if any(term in corpus for term in ("llm", "language", "multimodal", "vision-language")):
        tech.append(Resource(name="Hugging Face Transformers", kind="technology", url="https://huggingface.co/docs/transformers", verified=True, official=True, description="Library for transformer models and training workflows.", relevance="Useful for multimodal/LLM baselines, tokenizers, and model interoperability."))
    return tech


async def github_repositories(topic: str) -> tuple[list[Resource], SourceStatus]:
    words = re.findall(r"[a-zA-Z0-9-]{3,}", topic)[:7]
    query = " ".join(words)
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get("https://api.github.com/search/repositories", params={"q": query, "sort": "stars", "order": "desc", "per_page": 5}, headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            items = response.json().get("items", [])
            if not items:
                fallback = " ".join(words[:3]) or "machine learning"
                response = await client.get("https://api.github.com/search/repositories", params={"q": fallback, "sort": "stars", "order": "desc", "per_page": 5}, headers={"Accept": "application/vnd.github+json"})
                response.raise_for_status()
                items = response.json().get("items", [])
        resources = [Resource(name=item["full_name"], kind="repository", url=item["html_url"], verified=True, official=False, description=item.get("description") or "GitHub repository with no description.", relevance=f"Returned by GitHub's repository search for the research topic ({item.get('stargazers_count', 0)} stars). Inspect the README and paper association before treating it as an official implementation.", evidence="Verified through GitHub API.") for item in items]
        return resources, SourceStatus(source="github", succeeded=True, count=len(resources))
    except httpx.HTTPError as error:
        return [], SourceStatus(source="github", succeeded=False, error=str(error))


async def discover_resources(topic: str, papers: list[Paper]) -> tuple[list[Resource], SourceStatus]:
    repos, status = await github_repositories(topic)
    resources = repos + dataset_candidates(papers) + technology_candidates(topic, papers)
    return resources, status
