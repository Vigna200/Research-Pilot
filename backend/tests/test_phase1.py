from app.planner import build_plan
from app.ranking import rank_papers
from app.schemas import Paper
from app.sources import deduplicate

def test_planner_produces_multiple_queries():
    plan = build_plan("Find research gaps in multimodal LLMs for medical image analysis")
    assert len(plan.queries) >= 3
    assert "multimodal" in plan.terms

def test_deduplication_prefers_merged_record():
    papers = [Paper(id="a", title="A useful paper", doi="10.1/test", sources=["openalex"]), Paper(id="b", title="A useful paper", doi="10.1/test", abstract="Evidence", sources=["semantic_scholar"])]
    merged = deduplicate(papers)
    assert len(merged) == 1 and merged[0].abstract == "Evidence"
    assert set(merged[0].sources) == {"openalex", "semantic_scholar"}

def test_ranking_rewards_question_overlap():
    papers = [Paper(id="a", title="Multimodal LLMs for medical image analysis"), Paper(id="b", title="Quantum networking overview")]
    ranked = rank_papers(papers, "multimodal LLMs for medical image analysis")
    assert ranked[0].id == "a" and ranked[0].ranking_score > ranked[1].ranking_score
