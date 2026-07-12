from fastapi import HTTPException, status


class AIServiceException(Exception):
    """Base exception for AI evaluation service errors."""
    pass


class LLMProviderError(AIServiceException):
    """Raised when LLM provider API calls fail."""
    pass


class EmbeddingError(AIServiceException):
    """Raised when embedding generation or retrieval fails."""
    pass


class ValidationError(AIServiceException):
    """Raised when input validation fails."""
    pass


class ConfidenceThresholdError(AIServiceException):
    """Raised when extraction confidence is below threshold."""
    pass


class DatabaseError(AIServiceException):
    """Raised when database operations fail."""
    pass


class KafkaError(AIServiceException):
    """Raised when Kafka operations fail."""
    pass


def http_exception_handler(exc: AIServiceException) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    if isinstance(exc, LLMProviderError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider error: {str(exc)}"
        )
    elif isinstance(exc, EmbeddingError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service error: {str(exc)}"
        )
    elif isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(exc)}"
        )
    elif isinstance(exc, ConfidenceThresholdError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Confidence threshold error: {str(exc)}"
        )
    elif isinstance(exc, DatabaseError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}"
        )
    elif isinstance(exc, KafkaError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Kafka error: {str(exc)}"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal service error: {str(exc)}"
        )
