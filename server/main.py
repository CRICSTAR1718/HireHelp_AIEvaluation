from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from server.config.settings import settings
from server.config.db import engine, Base
from server.common.middleware.logging import setup_logging, log_requests
from server.common.middleware.error_handler import (
    http_exception_handler_middleware,
    validation_exception_handler,
    service_exception_handler,
    general_exception_handler
)
from server.common.exceptions import AIServiceException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Create database tables (in production, use Alembic migrations instead)
    if settings.DEBUG:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created (DEBUG mode)")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Evaluation Service - Resume parsing, screening, fitment scoring, and AI interviews",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.middleware("http")(log_requests)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler_middleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AIServiceException, service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
from server.health import router as health_router
app.include_router(health_router, tags=["Health"])

# Feature routers
from server.resume_parser.router import router as resume_parser_router
app.include_router(resume_parser_router, prefix="/api/v1/resume-parser", tags=["Resume Parser"])

from server.resume_screening.router import router as resume_screening_router
app.include_router(resume_screening_router, prefix="/api/v1/resume-screening", tags=["Resume Screening"])

from server.fitment_score.router import router as fitment_score_router
app.include_router(fitment_score_router, prefix="/api/v1/fitment-score", tags=["Fitment Score"])

from server.ai_interview.router import router as ai_interview_router
app.include_router(ai_interview_router, prefix="/api/v1/ai-interview", tags=["AI Interview"])

from server.jd_matching.router import router as jd_matching_router
app.include_router(jd_matching_router, prefix="/api/v1/jd-matching", tags=["Job Description Matching"])

from server.skill_extraction.router import router as skill_extraction_router
app.include_router(skill_extraction_router, prefix="/api/v1/skill-extraction", tags=["Skill Extraction"])

from server.answer_evaluation.router import router as answer_evaluation_router
app.include_router(answer_evaluation_router, prefix="/api/v1/answer-evaluation", tags=["Answer Evaluation"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
