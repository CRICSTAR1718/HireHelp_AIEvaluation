# AI Agent Instructions — `ai-evaluation-service`

Paste this at the top of the repo (e.g. `AGENTS.md` or `CLAUDE.md`) so any AI agent working in this codebase follows the same rules as the rest of the team.

---

### Scope of this repo
This repo owns the **AI/LLM domain only**: resume parsing, resume screening, JD/skill matching, fitment scoring, and the AI-driven interview. It does **not** own candidate profiles, job requisitions, interview scheduling, or notifications — those live in `candidate-service`, `recruitment-service`, `interview-service`, and `communication-service` respectively. If a task needs data from one of those domains, call that service's API — never duplicate its logic or query its database here.

This is the **only Python service** in the platform. Every other service is Express + TypeScript — don't import patterns from those repos, and don't let this repo's conventions leak into them.

### Tech stack — do not deviate
- **FastAPI** (not Flask, not Django)
- **Pydantic v2** for every request/response schema — no untyped dicts crossing a route boundary
- **PostgreSQL** — this service's own schema, accessed via SQLAlchemy or a lightweight query layer (confirm with team which — don't introduce a second ORM style mid-service)
- **LangChain/LangGraph** (or direct provider SDK calls) for LLM orchestration — isolate all prompt logic in `prompts/` and `llm/`, never inline a prompt string inside a router or service function
- **pytest** for tests
- **Qdrant client** or **pgvector** for embeddings — confirm which is actually running in `docker-compose.yml` before adding either as a new dependency
- This service's DB is private — no other service, and no other repo's agent, should ever query it directly

### Folder structure — follow exactly, don't reorganize
```
ai-evaluation-service/
├── server/
│   ├── config/
│   │   ├── settings.py          env loading (Pydantic Settings), constants
│   │   └── db.py                  DB session/engine setup
│   ├── common/
│   │   ├── middleware/
│   │   │   ├── auth.py             JWT verification (service-to-service or gateway-forwarded claims)
│   │   │   ├── error_handler.py
│   │   │   └── logging.py
│   │   └── exceptions.py
│   ├── database/
│   │   ├── models.py               SQLAlchemy models / table definitions
│   │   └── migrations/             Alembic migrations
│   ├── resume_parser/
│   │   ├── router.py                FastAPI APIRouter, path operations only
│   │   ├── service.py                business logic, calls llm/ and prompts/
│   │   ├── schema.py                 Pydantic request/response models
│   │   └── test_resume_parser.py
│   ├── resume_screening/           (same 4-file pattern)
│   ├── jd_matching/
│   ├── skill_extraction/
│   ├── ai_interview/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── question_generator.py    isolated question-generation logic
│   │   ├── conversation_manager.py  session/state handling for multi-turn interviews
│   │   ├── schema.py
│   │   └── test_ai_interview.py
│   ├── answer_evaluation/
│   ├── fitment_score/
│   │   ├── router.py
│   │   ├── scoring_engine.py        weighting/scoring logic, isolated and unit-tested
│   │   ├── schema.py
│   │   └── test_fitment_score.py
│   ├── recommendation/
│   ├── llm/
│   │   ├── client.py                 provider wrapper (OpenAI/Gemini/Claude) — all LLM calls go through here
│   │   └── provider_config.py
│   ├── prompts/
│   │   ├── resume_parsing.txt
│   │   ├── fitment_scoring.txt
│   │   └── interview_questions.txt
│   ├── embeddings/
│   │   ├── embedding_service.py
│   │   └── vector_client.py          pgvector or Qdrant, behind one interface
│   ├── events/
│   │   └── handlers/
│   │       └── resume_uploaded_handler.py
│   ├── health.py                     GET /health
│   └── main.py                       FastAPI app instance, router registration, startup/shutdown events
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```
Every feature = `router.py` (routes only, no business logic) + `service.py` (logic, calls `llm/` and `prompts/`) + `schema.py` (Pydantic models) + `test_<feature>.py`. Routers are registered in `main.py` via `app.include_router(...)` — don't mount routes anywhere else.

### LLM & prompt rules
- **No inline prompts.** Every prompt lives in `prompts/*.txt` (or `.jinja` if templated) and is loaded by the calling service — never construct a prompt string directly inside `service.py`.
- **All LLM calls go through `llm/client.py`.** Don't call `openai.chat.completions...` or any provider SDK directly from a feature module — the wrapper is what lets the team swap providers, add retries, and track token usage in one place.
- **Every fitment score must include reasoning**, never a bare number — this is a product requirement, not just a nice-to-have (see PRD Section 6.3). If a prompt or scoring change would produce a score without an explanation, don't ship it.
- Low-confidence extractions (resume parsing) must be flagged for human review, not silently defaulted — surface a `confidence` field on parsed fields rather than guessing.
- Log token usage and latency per LLM call (span attributes if OpenTelemetry is wired) — bulk resume uploads make cost/latency visible fast, don't fly blind here.

### API contract rules
- Every request/response validated with a Pydantic model — FastAPI will reject invalid payloads automatically, but don't bypass this by accepting raw `dict`/`Request` bodies unless there's a specific streaming reason to.
- This service is called by other Node services over internal HTTP (e.g. `recruitment-service` triggering a fitment sweep) — keep internal endpoints documented in `README.md` separately from any public-facing ones the gateway proxies.
- Don't change an existing endpoint's request/response shape without checking `recruitment-service`'s and `candidate-service`'s HTTP clients that call this service.

### Do not modify without team approval
- `database/models.py` structure
- `llm/client.py`'s provider interface (other modules depend on its method signatures)
- Fitment scoring weights in `fitment_score/scoring_engine.py` — changing these changes every candidate's score platform-wide, coordinate before touching
- Folder structure above

### Coding standards
- Feature-first, one folder per capability as shown above
- No business logic in routers — router calls service, service calls llm/prompts/db as needed
- Type everything with Pydantic models; no bare `dict` crossing a function boundary that represents a domain object
- Comments only where the "why" isn't obvious (e.g. why a confidence threshold is set where it is) — don't narrate what the code already says
- Every new endpoint gets a matching `test_*.py` before merge, including at least one test with a mocked LLM response (never hit a real LLM API in CI)

### Before opening a PR
- `pytest` passes locally, with LLM calls mocked
- New/changed routes reflected in the service's README and FastAPI's auto-generated OpenAPI docs
- No `.env` values or API keys committed
- If a prompt was changed, note what changed and why in the PR description — prompt changes are effectively logic changes and should be reviewable as such
