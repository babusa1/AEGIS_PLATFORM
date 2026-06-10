"""
API Dependencies - Doctor API
=============================

This module provides common FastAPI dependencies used across endpoints.

Dependencies handle:
- Database session injection
- Current user authentication
- Service instantiation
- Common validation

Usage:
    from api.deps import get_current_user, get_db
    
    @router.get("/protected")
    async def protected_route(
        current_user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        ...
"""

import os
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import BaseModel
import requests

from db.session import get_doctor_db, get_patient_db
from core.config import settings
from core.exceptions import AuthenticationError
from core.logging import get_logger

logger = get_logger(__name__)

# OAuth2 scheme for Bearer token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # Don't raise error if token is missing (for local dev mode)
)

# =============================================================================
# LOCAL DEVELOPMENT MODE TEST USER
# =============================================================================
# When LOCAL_DEV_MODE=true, this is used as the default test doctor
LOCAL_DEV_TEST_USER_ID = "22222222-2222-2222-2222-222222222222"
LOCAL_DEV_TEST_EMAIL = "test.doctor@oncolife.local"


# =============================================================================
# Token Data Model
# =============================================================================

class TokenData(BaseModel):
    """
    Data extracted from a validated JWT token.
    
    Attributes:
        sub: The user's unique ID (Cognito 'sub' claim)
        email: The user's email address (optional)
    """
    sub: str
    email: Optional[str] = None


# =============================================================================
# JWKS Cache
# =============================================================================

_jwks_cache = {}


def _get_jwks():
    """
    Fetch and cache the JSON Web Key Set from Cognito.
    
    The JWKS contains the public keys used to verify JWTs.
    """
    global _jwks_cache
    
    if _jwks_cache:
        return _jwks_cache
    
    if not settings.cognito_jwks_url:
        logger.error("Cognito JWKS URL not configured")
        raise HTTPException(
            status_code=500,
            detail="Authentication service not configured"
        )
    
    try:
        response = requests.get(settings.cognito_jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not fetch security keys"
        )


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme)
) -> TokenData:
    """
    Validate the JWT token and return the current user's data.
    
    In LOCAL_DEV_MODE, returns a test user without requiring authentication.
    
    This is the main authentication dependency that protects routes.
    
    Args:
        token: The Bearer token from the Authorization header
        
    Returns:
        TokenData with the user's ID and email
        
    Raises:
        HTTPException: If token is invalid or expired (401)
    """
    # Local development bypass - no authentication required
    if settings.local_dev_mode:
        logger.debug("LOCAL_DEV_MODE: Using test doctor user")
        return TokenData(
            sub=LOCAL_DEV_TEST_USER_ID,
            email=LOCAL_DEV_TEST_EMAIL,
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        # Get JWKS
        jwks = _get_jwks()
        
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        
        # Find the matching public key
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break
        
        if not rsa_key:
            logger.error("No matching public key found in JWKS")
            raise credentials_exception
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.cognito_issuer,
        )
        
        # Extract user data
        user_id = payload.get("sub")
        if not user_id:
            logger.error("Token missing 'sub' claim")
            raise credentials_exception
        
        return TokenData(
            sub=user_id,
            email=payload.get("email"),
        )
        
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise credentials_exception


async def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(
        tokenUrl="/api/v1/auth/login",
        auto_error=False,  # Don't raise error if token is missing
    ))
) -> Optional[TokenData]:
    """
    Optionally validate the JWT token if present.
    
    Use this for routes that can work with or without authentication.
    
    Args:
        token: The Bearer token (optional)
        
    Returns:
        TokenData if token is valid, None otherwise
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


# =============================================================================
# Database Dependencies
# =============================================================================

def get_doctor_db_session() -> Generator[Session, None, None]:
    """
    Alias for get_doctor_db for cleaner imports.
    """
    yield from get_doctor_db()


def get_patient_db_session() -> Generator[Session, None, None]:
    """
    Alias for get_patient_db for cleaner imports.
    """
    yield from get_patient_db()





