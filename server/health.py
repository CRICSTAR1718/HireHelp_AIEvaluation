from fastapi import APIRouter
from typing import Dict, Any
from sqlalchemy import text
from server.config.db import engine
from server.config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns service status and dependency health.
    """
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "dependencies": {}
    }
    
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check LLM provider configuration
    try:
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            health_status["dependencies"]["llm_provider"] = "configured"
        elif settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            health_status["dependencies"]["llm_provider"] = "configured"
        elif settings.LLM_PROVIDER == "claude" and settings.CLAUDE_API_KEY:
            health_status["dependencies"]["llm_provider"] = "configured"
        else:
            health_status["dependencies"]["llm_provider"] = "not_configured"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"LLM provider health check failed: {str(e)}")
        health_status["dependencies"]["llm_provider"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status
