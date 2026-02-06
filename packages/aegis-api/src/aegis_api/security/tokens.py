"""
JWT Token Management

Token creation, refresh, and validation utilities.
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
import structlog

from aegis.config import get_settings

logger = structlog.get_logger(__name__)


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    """
    Create a JWT refresh token (longer expiration).
    
    Args:
        user_id: User ID
        tenant_id: Tenant ID
        
    Returns:
        Encoded JWT refresh token
    """
    settings = get_settings()
    secret = settings.auth.jwt_secret_key.get_secret_value()
    algorithm = settings.auth.jwt_algorithm
    
    # Refresh tokens expire in 7 days
    expire = datetime.utcnow() + timedelta(days=7)
    
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def refresh_access_token(refresh_token: str) -> str:
    """
    Create a new access token from a refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    from fastapi import HTTPException
    
    settings = get_settings()
    secret = settings.auth.jwt_secret_key.get_secret_value()
    algorithm = settings.auth.jwt_algorithm
    
    try:
        payload = jwt.decode(refresh_token, secret, algorithms=[algorithm])
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        
        if not user_id or not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Create new access token
        from aegis_api.security.auth import create_access_token
        return create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=payload.get("role", "user"),
            email=payload.get("email"),
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")
