"""Gemini-backed query planner with deterministic fallback. No key means no network LLM call."""
import json
import httpx
from .config import settings
from .schemas import SearchPlan
from .bedrock_agents import BedrockAgentUnavailable, invoke_research_planner

async def plan_with_genai(question: str, fallback: SearchPlan) -> SearchPlan:
    if settings.genai_provider.lower() == "bedrock_agent":
        try:
            parsed = json.loads(invoke_research_planner(question))
            plan = SearchPlan.model_validate(parsed)
            return plan if plan.queries else fallback
        except (BedrockAgentUnavailable, ValueError, json.JSONDecodeError):
            return fallback
    if settings.genai_provider.lower() != "gemini" or not settings.gemini_api_key:
        return fallback
    prompt = ("Return JSON only with keys topic, subtopics, queries, terms. Create 3-5 precise scholarly search queries. "
              "Do not invent papers, datasets, or claims. Research question: " + question)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.genai_model}:generateContent?key={settings.gemini_api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(url, json=payload); response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        plan = SearchPlan.model_validate(parsed)
        return plan if plan.queries else fallback
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
        return fallback
