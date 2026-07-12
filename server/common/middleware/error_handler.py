from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from server.common.exceptions import AIServiceException, http_exception_handler
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler_middleware(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions with consistent error response format."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )


async def service_exception_handler(
    request: Request,
    exc: AIServiceException
) -> JSONResponse:
    """Handle custom service exceptions."""
    logger.error(f"Service error: {type(exc).__name__} - {str(exc)}")
    
    http_exc = http_exception_handler(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "error": {
                "type": type(exc).__name__,
                "message": http_exc.detail,
                "status_code": http_exc.status_code
            }
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred",
                "status_code": 500
            }
        }
    )
