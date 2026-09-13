import jwt
import time
import logging
from typing import Optional
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)

def get_jwt_secret() -> str:
    secret = settings.jwt_secret.strip()
    if not secret:
        # Fallback consistent secret if not set
        return "smartnote-default-jwt-secret-do-not-use-in-production"
    return secret

def create_session_token(user_id: str, expiration_days: Optional[int] = None) -> str:
    """Creates a signed HS256 JWT for the mobile client session."""
    days = expiration_days or settings.jwt_expiration_days
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + (days * 86400)
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=settings.jwt_algorithm)

def verify_session_token(token: str) -> Optional[str]:
    """Decodes token and returns user_id (sub) or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        logger.warning("Session JWT expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid session JWT: {e}")
        return None

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> str:
    """
    FastAPI dependency extracting the authenticated user_id from the Bearer JWT.
    Falls back to 'default_user' if no token is provided (for initial open endpoints / migration).
    """
    if auth and auth.credentials:
        user_id = verify_session_token(auth.credentials)
        if user_id:
            return user_id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Default tenant for unauthenticated requests
    return "default_user"

async def require_authenticated_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> str:
    """Strict dependency requiring valid JWT session."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    user_id = verify_session_token(auth.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_id
