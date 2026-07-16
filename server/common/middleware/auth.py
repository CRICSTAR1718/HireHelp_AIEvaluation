from fastapi import Request, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import jwt
from ..exceptions import AIServiceException


security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


async def verify_service_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_internal_service: Optional[str] = Header(None, alias="x-internal-service")
) -> dict:
    """
    Verify service authentication via either:
    1. Authorization: Bearer token (JWT or shared secret)
    2. x-internal-service header (internal service allowlist)
    
    SECURITY NOTE: x-internal-service is a weak, spoofable trust mechanism.
    Real inter-service auth (mTLS, shared-secret JWTs, service mesh) should replace it before production.
    """
    from ...config.settings import settings
    
    # Path 1: Authorization: Bearer present
    if credentials:
        token = credentials.credentials
        
        # Mode 1: JWT verification
        if settings.JWT_SECRET_KEY:
            try:
                claims = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                return {
                    "service": claims.get("service", "unknown"),
                    "sub": claims.get("sub"),
                    "roles": claims.get("roles", []),
                    "user_id": claims.get("sub"),
                    "auth_method": "jwt"
                }
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            except jwt.InvalidTokenError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}"
                )
        
        # Mode 2: Shared secret token
        elif settings.SERVICE_TOKEN:
            if token != settings.SERVICE_TOKEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid service token"
                )
            return {
                "service": "service-token",
                "user_id": None,
                "roles": [],
                "auth_method": "service_token"
            }
        
        # Mode 3: Dev-only mode (insecure)
        else:
            logger.warning(
                "SECURITY WARNING: Running in dev-only mode with no JWT_SECRET_KEY or SERVICE_TOKEN set. "
                "Any non-empty Bearer token is accepted. This is insecure and should NOT be used in production."
            )
            return {
                "service": "dev-mode",
                "user_id": None,
                "roles": [],
                "auth_method": "dev_mode"
            }
    
    # Path 2: x-internal-service header present
    elif x_internal_service:
        if x_internal_service not in settings.ALLOWED_INTERNAL_SERVICES:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Internal service '{x_internal_service}' not in allowlist"
            )
        return {
            "service": x_internal_service,
            "user_id": None,
            "roles": [],
            "auth_method": "internal_service_header"
        }
    
    # Path 3: No auth provided
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication: provide either Authorization: Bearer or x-internal-service header"
        )


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
