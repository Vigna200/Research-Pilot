from datetime import datetime
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    max_results: int = Field(default=20, ge=5, le=50)


class SignUpRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    phone_number: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: str
    password: str


class OtpVerifyRequest(BaseModel):
    challenge_id: str
    code: str = Field(min_length=6, max_length=6)


class AuthChallenge(BaseModel):
    challenge_id: str
    delivery: str
    expires_in_seconds: int
    development_code: str | None = None


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


class SearchPlan(BaseModel):
    topic: str
    subtopics: list[str]
    queries: list[str]
    terms: list[str]


class Paper(BaseModel):
    id: str
    title: str
    abstract: str | None = None
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None
    publisher: str | None = None
    issn: list[str] = []
    publication_type: str = "Other"
    doi: str | None = None
    url: str | None = None
    semantic_scholar_id: str | None = None
    citation_count: int = 0
    open_access: bool = False
    open_access_url: str | None = None
    sources: list[str] = []
    ranking_score: float = 0.0
    similarity_percent: int = 0
    ranking_reasons: list[str] = []
    verification_percent: int = 0
    verification_checks: list[str] = []
    ieee_citation: str | None = None
    evidence_confidence_percent: int = 0
    evidence_count: int = 0


class Resource(BaseModel):
    name: str
    kind: str
    url: str
    verified: bool
    official: bool = False
    description: str
    relevance: str
    evidence: str | None = None


class ResearchDirection(BaseModel):
    title: str
    research_question: str
    hypothesis: str
    rationale: str
    baselines: list[str]
    datasets: list[str]
    technology_stack: list[str]
    metrics: list[str]
    feasibility: str
    evidence_papers: list[str]


class ResearchGap(BaseModel):
    title: str
    gap_type: str
    statement: str
    status: str
    confidence: int
    evidence: list[str]
    what_exists: str
    next_step: str
    counter_evidence: list[str] = []
    validation_query: str | None = None


class StructuredPaperRecord(BaseModel):
    paper_id: str
    paper_title: str
    research_problem: str | None = None
    methods: list[str] = []
    datasets: list[str] = []
    metrics: list[str] = []
    results: list[str] = []
    limitations: list[str] = []
    evidence_level: str = "abstract"


class ComparisonMatrix(BaseModel):
    dimension: str
    rows: list[dict[str, str]]
    evidence_level: str = "abstract"


class Evidence(BaseModel):
    paper_id: str
    paper_title: str
    category: str
    claim: str
    evidence_text: str
    source_url: str | None = None
    evidence_level: str = "abstract"
    confidence_percent: int = 0
    provenance: str = "Abstract supplied by scholarly source"


class SourceStatus(BaseModel):
    source: str
    succeeded: bool
    count: int = 0
    error: str | None = None


class SessionCounts(BaseModel):
    discovered: int
    deduplicated: int
    ranked: int


class ResearchSession(BaseModel):
    id: str
    question: str
    created_at: datetime
    plan: SearchPlan
    papers: list[Paper]
    resources: list[Resource] = []
    recommendations: list[ResearchDirection] = []
    research_gaps: list[ResearchGap] = []
    evidence: list[Evidence] = []
    structured_papers: list[StructuredPaperRecord] = []
    comparisons: list[ComparisonMatrix] = []
    source_status: list[SourceStatus]
    counts: SessionCounts
