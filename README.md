# ResearchPilot

ResearchPilot is a topic-first research discovery platform. A researcher submits a question; the system builds a transparent search plan, discovers papers from scholarly APIs, deduplicates and ranks candidates, and retains source provenance for every record.

This repository currently delivers the first evidence-grounded workflow: automatic discovery, planning, merging, verification, ranking, durable sessions, abstract-level structured evidence, cross-paper comparison matrices, counter-evidence searches for gap candidates, and a React workspace. It deliberately labels full-text RAG and page-level claims as unavailable until legal open-access documents are retrieved and parsed.

## Quick start

```powershell
docker compose up --build
```

Open `http://localhost:5173`. The API is at `http://localhost:8000`; its interactive contract is at `/docs`.

For a local backend-only run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

Semantic Scholar works without a key at conservative rates; set `SEMANTIC_SCHOLAR_API_KEY` for a production deployment. OpenAlex has no required key. The app degrades gracefully if one source is unavailable and reports source-level failures in the session.

## Enable Gemini planning

Copy `backend/.env.example` to `backend/.env`, then set `GENAI_PROVIDER=gemini` and `GEMINI_API_KEY`. Gemini is used only to expand the research question into search queries; papers, evidence, citations, resources, and gap claims remain grounded in API results. Without a key, the deterministic planner is used.

## Accounts and project history

Research sessions are protected by a local account and are stored as projects for the authenticated user. Sign-up and every login require a password plus one-time verification. The default local configuration uses a **development OTP**, displayed only in the browser response; it does not send SMS. Before deployment set a strong `AUTH_SECRET`, set `OTP_DEVELOPMENT_MODE=false`, and integrate an approved SMS provider. Phone verification cannot be represented as delivered until that provider is configured.

## Optional AWS Bedrock Agent integration

Boto3 is included as an optional Bedrock Agent bridge. Set `AWS_REGION`, `BEDROCK_AGENT_ID`, and `BEDROCK_AGENT_ALIAS_ID` in `backend/.env`, then provide AWS credentials through the normal AWS credential chain or an IAM runtime role. Configure the Bedrock Agent with narrowly scoped planning tools/action groups. ResearchPilot keeps scholarly retrieval, verification, and evidence grounding in its own pipeline; an agent response is never treated as evidence by itself.

## Publisher and full-text access

IEEE-style citations are a formatting style and do not indicate that a work is an IEEE publication. ResearchPilot displays a full-text link only when an API provides an open-access URL. It does not bypass IEEE Xplore or any publisher paywall; otherwise it retains the metadata/source record only.

See [docs/architecture.md](docs/architecture.md) for the approved architecture, data flow, API contract, retrieval and gap algorithms, provenance model, evaluation plan, and phased roadmap.
