# AI Evaluation Service

AI-powered resume parsing, screening, fitment scoring, and AI interview service for the HireHelp platform.

## Scope

This service owns the **AI/LLM domain only**:
- Resume parsing
- Resume screening
- JD/skill matching
- Fitment scoring
- AI-driven interviews

It does **not** own candidate profiles, job requisitions, interview scheduling, or notifications — those live in `candidate-service`, `recruitment-service`, `interview-service`, and `communication-service` respectively.

## Tech Stack

- **FastAPI** - Web framework
- **Pydantic v2** - Request/response validation
- **PostgreSQL** - Database with SQLAlchemy
- **LangChain/LangGraph** - LLM orchestration
- **OpenAI/Gemini/Claude** - LLM providers
- **Qdrant/pgvector** - Vector embeddings
- **pytest** - Testing

## Project Structure

```
ai-evaluation-service/
├── server/
│   ├── config/                 # Configuration and database setup
│   ├── common/                 # Shared middleware and exceptions
│   ├── database/               # SQLAlchemy models and migrations
│   ├── resume_parser/          # Resume parsing feature
│   ├── resume_screening/       # Resume screening feature
│   ├── jd_matching/            # Job description matching
│   ├── skill_extraction/       # Skill extraction
│   ├── ai_interview/           # AI interview feature
│   ├── answer_evaluation/      # Answer evaluation
│   ├── fitment_score/          # Fitment scoring
│   ├── recommendation/         # Recommendations
│   ├── llm/                    # LLM client wrapper
│   ├── prompts/                # Prompt templates
│   ├── embeddings/             # Embedding service
│   ├── health.py               # Health check endpoint
│   └── main.py                 # FastAPI application
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- OpenAI/Gemini/Claude API key

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your environment variables
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run database migrations:

```bash
cd server
alembic upgrade head
```

5. Start the service:

```bash
python -m server.main
```

Or using uvicorn directly:

```bash
uvicorn server.main:app --reload
```

### Docker

Build and run with Docker:

```bash
docker build -t ai-evaluation-service .
docker run -p 8000:8000 --env-file .env ai-evaluation-service
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

## Internal API Endpoints

These endpoints are called by other services over internal HTTP:

### Resume Parser
- `POST /api/v1/resume-parser/parse` - Parse a resume
- `GET /api/v1/resume-parser/{resume_id}` - Get parsed resume

### Resume Screening
- `POST /api/v1/resume-screening/screen` - Screen a resume against a job
- `GET /api/v1/resume-screening/{screening_id}` - Get screening result

### Fitment Score
- `POST /api/v1/fitment-score/calculate` - Calculate fitment score
- `GET /api/v1/fitment-score/{score_id}` - Get fitment score

### AI Interview
- `POST /api/v1/ai-interview/start` - Start an AI interview
- `POST /api/v1/ai-interview/answer` - Submit answer
- `GET /api/v1/ai-interview/{interview_id}` - Get interview status

### Job Description Matching
- `POST /api/v1/jd-matching/match` - Match job description to candidates using semantic search

### Skill Extraction
- `POST /api/v1/skill-extraction/extract` - Extract skills from text (resume or job description)
- `GET /api/v1/skill-extraction/{extraction_id}` - Get skill extraction result

### Answer Evaluation
- `POST /api/v1/answer-evaluation/evaluate` - Evaluate an interview answer using AI
- `GET /api/v1/answer-evaluation/{evaluation_id}` - Get answer evaluation result

## Development

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=server --cov-report=html
```

### Adding New Features

Each feature should follow the pattern:
- `router.py` - FastAPI routes only
- `service.py` - Business logic (calls llm/ and prompts/)
- `schema.py` - Pydantic request/response models
- `test_<feature>.py` - Tests with mocked LLM responses

### LLM & Prompt Rules

- **No inline prompts** - Every prompt lives in `prompts/*.txt`
- **All LLM calls go through `llm/client.py`**
- **Every fitment score must include reasoning**
- Log token usage and latency per LLM call

## Coding Standards

- Feature-first, one folder per capability
- No business logic in routers
- Type everything with Pydantic models
- Comments only where the "why" isn't obvious
- Every new endpoint gets a matching test

## Before Opening a PR

- `pytest` passes locally, with LLM calls mocked
- New/changed routes reflected in README and OpenAPI docs
- No `.env` values or API keys committed
- If prompt was changed, note what changed and why in PR description

## License

Internal HireHelp service - All rights reserved
