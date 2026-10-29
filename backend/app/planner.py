import re
from .schemas import SearchPlan

STOP_WORDS = {"research", "gaps", "gap", "in", "for", "the", "and", "of", "on", "with", "find", "analysis", "a", "an"}


def build_plan(question: str) -> SearchPlan:
    cleaned = re.sub(r"^(find|identify|analyse|analyze)\\s+(research\\s+)?gaps?\\s+(in|for)\\s+", "", question.strip(), flags=re.I)
    tokens = [x for x in re.findall(r"[A-Za-z0-9-]{3,}", cleaned.lower()) if x not in STOP_WORDS]
    topic = cleaned.rstrip("?. ")
    core = " ".join(tokens[:6]) or topic
    phrases = [topic, core]
    if "multimodal" in tokens:
        phrases.extend([f"{core} vision language", f"{core} multimodal learning"])
    else:
        phrases.extend([f"{core} methods", f"{core} evaluation"])
    queries = list(dict.fromkeys(p for p in phrases if p))[:5]
    return SearchPlan(topic=topic, subtopics=tokens[:8], queries=queries, terms=tokens)
