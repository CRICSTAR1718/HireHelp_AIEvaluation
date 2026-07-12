from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..exceptions import AIServiceException


security = HTTPBearer()


async def verify_service_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = security
) -> dict:
    """
    Verify JWT token for service-to-service communication.
    Extracts and validates claims from the token.
    """
    from ..config.settings import settings
    
    token = credentials.credentials
    
    # TODO: Implement actual JWT verification
    # For now, this is a placeholder that checks if token is present
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    # In production, decode and verify JWT signature
    # claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    # Placeholder claims - replace with actual JWT decoding
    claims = {
        "service": "ai-evaluation-service",
        "user_id": None,
        "roles": []
    }
    
    return claims


async def verify_gateway_claims(request: Request) -> dict:
    """
    Verify claims forwarded by API gateway.
    Gateway handles JWT validation, we extract user context.
    """
    user_id = request.headers.get("X-User-ID")
    roles = request.headers.get("X-User-Roles", "").split(",") if request.headers.get("X-User-Roles") else []
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user context from gateway"
        )
    
    return {
        "user_id": user_id,
        "roles": roles,
        "service": "gateway"
    }
