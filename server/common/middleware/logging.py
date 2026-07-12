from fastapi import Request
import logging
import time
from typing import Callable
from server.config.settings import settings

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next: Callable):
    """
    Middleware to log all incoming requests with timing information.
    """
    start_time = time.time()
    
    # Log request details
    logger.info(
        f"Incoming request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    process_time = time.time() - start_time
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response details
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"with status {response.status_code} in {process_time:.3f}s"
    )
    
    return response


def setup_logging():
    """
    Configure application logging based on environment.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Suppress noisy third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)
