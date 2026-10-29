from datetime import datetime, timezone
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .planner import build_plan
from .ranking import rank_papers
from .schemas import AuthChallenge, AuthToken, LoginRequest, OtpVerifyRequest, ResearchRequest, ResearchSession, SessionCounts, SignUpRequest
from .sources import deduplicate, discover
from .resources import discover_resources
from .verification import verify_papers
from .directions import recommend
from .gaps import analyze_gaps
from .evidence import extract_evidence
from .genai import plan_with_genai
from .database import initialise_database, load_session, projects_for_user, save_project, save_session, session_belongs_to_user
from .analysis import structured_analysis
from .validation import validate_gaps
from .auth import current_user, login, sign_up, verify_otp

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_database()
    yield

app = FastAPI(title="ResearchPilot API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    return {
        "name": "ResearchPilot API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "research_endpoint": "/api/v1/research-sessions",
    }

@app.get("/health")
async def health(): return {"status": "ok", "phase": 1}

@app.post("/api/v1/auth/sign-up", response_model=AuthChallenge, status_code=201)
async def auth_sign_up(request: SignUpRequest): return sign_up(request)

@app.post("/api/v1/auth/login", response_model=AuthChallenge)
async def auth_login(request: LoginRequest): return login(request)

@app.post("/api/v1/auth/verify-otp", response_model=AuthToken)
async def auth_verify_otp(request: OtpVerifyRequest): return verify_otp(request)

@app.get("/api/v1/projects")
async def list_projects(user: dict[str, str] = Depends(current_user)):
    return [{"id": p.id, "session_id": p.session_id, "title": p.title, "created_at": p.created_at} for p in projects_for_user(user["id"])]

@app.post("/api/v1/research-sessions", response_model=ResearchSession, status_code=201)
async def create_research_session(request: ResearchRequest, user: dict[str, str] = Depends(current_user)):
    plan = await plan_with_genai(request.question, build_plan(request.question))
    raw, source_status = await discover(plan.queries, max(3, request.max_results // len(plan.queries)))
    if not raw:
        raise HTTPException(503, detail={"message": "No scholarly source responded", "sources": [s.model_dump() for s in source_status]})
    unique = deduplicate(raw)
    ranked = rank_papers(unique, request.question)[:5]
    verification_status = await verify_papers(ranked)
    resources, github_status = await discover_resources(plan.topic, ranked)
    research_gaps = analyze_gaps(request.question, ranked)
    research_gaps, counter_search_papers = await validate_gaps(request.question, research_gaps, ranked)
    evidence = extract_evidence(ranked)
    structured_papers, comparisons = structured_analysis(ranked)
    recommendations = recommend(request.question, ranked, resources)
    recommendations.extend(
        [
            {
                "title": f"{gap.status}: {gap.title}",
                "research_question": gap.next_step,
                "hypothesis": "The candidate should be tested only after a targeted counter-evidence search confirms the corpus signal.",
                "rationale": gap.statement,
                "baselines": [paper.title for paper in ranked[:3]],
                "datasets": [resource.name for resource in resources if resource.kind == "dataset"] or ["Select a licensed dataset appropriate to the validation question"],
                "technology_stack": [resource.name for resource in resources if resource.kind == "technology"],
                "metrics": ["Evidence coverage", "Counter-evidence rate", "Task-specific primary metric"],
                "feasibility": f"Corpus confidence: {gap.confidence}%",
                "evidence_papers": gap.evidence,
            }
            for gap in research_gaps
        ]
    )
    session = ResearchSession(id=str(uuid4()), question=request.question, created_at=datetime.now(timezone.utc), plan=plan, papers=ranked, resources=resources, recommendations=recommendations, research_gaps=research_gaps, evidence=evidence, structured_papers=structured_papers, comparisons=comparisons, source_status=source_status + [verification_status, github_status], counts=SessionCounts(discovered=len(raw), deduplicated=len(unique), ranked=len(ranked)))
    save_session(session)
    save_project(user["id"], session.id, session.plan.topic, session.created_at)
    return session

@app.get("/api/v1/research-sessions/{session_id}", response_model=ResearchSession)
async def get_research_session(session_id: str, user: dict[str, str] = Depends(current_user)):
    if not session_belongs_to_user(user["id"], session_id): raise HTTPException(404, detail="Research session not found")
    payload = load_session(session_id)
    if not payload: raise HTTPException(404, detail="Research session not found")
    return ResearchSession.model_validate(payload)
