"""
Authentication utilities with JWT support.
"""

from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timedelta
import structlog
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)


@dataclass
class User:
    """Authenticated user."""
    id: str
    tenant_id: str
    role: str
    email: str | None = None
    name: str | None = None
    permissions: list[str] | None = None


def get_jwt_secret() -> str:
    """Get JWT secret from settings."""
    try:
        from aegis.config import get_settings
        settings = get_settings()
        return settings.auth.jwt_secret_key.get_secret_value()
    except Exception:
        # Fallback for development
        return "jwt-secret-change-me"


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    email: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID
        tenant_id: Tenant ID
        role: User role
        email: User email
        expires_delta: Token expiration time (default: 30 minutes)
        
    Returns:
        Encoded JWT token
    """
    try:
        from aegis.config import get_settings
        settings = get_settings()
        secret = settings.auth.jwt_secret_key.get_secret_value()
        algorithm = settings.auth.jwt_algorithm
        expire_minutes = settings.auth.jwt_access_token_expire_minutes
    except Exception:
        secret = "jwt-secret-change-me"
        algorithm = "HS256"
        expire_minutes = 30
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    
    payload = {
        "sub": user_id,  # Subject (user ID)
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        from aegis.config import get_settings
        settings = get_settings()
        secret = settings.auth.jwt_secret_key.get_secret_value()
        algorithm = settings.auth.jwt_algorithm
    except Exception:
        secret = "jwt-secret-change-me"
        algorithm = "HS256"
    
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Supports:
    - JWT Bearer token (production)
    - Development mode with headers (when no token)
    """
    # Check if we're in development mode and no token provided
    try:
        from aegis.config import get_settings
        settings = get_settings()
        mock_mode = settings.app.mock_mode
    except Exception:
        mock_mode = True
    
    # Development mode - return mock user if no credentials
    if not credentials and mock_mode:
        tenant_id = request.headers.get("X-Tenant-ID", "dev-tenant")
        role = request.headers.get("X-Role", "physician")
        
        logger.debug("Using mock user (development mode)", tenant_id=tenant_id, role=role)
        return User(
            id="dev-user",
            tenant_id=tenant_id,
            role=role,
            email="dev@aegis.local",
            name="Development User",
            permissions=["read", "write"],
        )
    
    # Require token if not in mock mode
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate JWT token
    token = credentials.credentials
    payload = decode_token(token)
    
    # Extract user information from token
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")
    email = payload.get("email")
    
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
        )
    
    # Determine permissions based on role
    permissions = []
    if role == "admin":
        permissions = ["read", "write", "admin", "delete"]
    elif role in ["physician", "nurse", "provider"]:
        permissions = ["read", "write"]
    elif role == "patient":
        permissions = ["read"]
    else:
        permissions = ["read"]
    
    logger.debug("Authenticated user", user_id=user_id, tenant_id=tenant_id, role=role)
    
    return User(
        id=user_id,
        tenant_id=tenant_id,
        role=role,
        email=email,
        name=payload.get("name"),
        permissions=permissions,
    )


def require_role(*roles: str):
    """
    Decorator to require specific roles.
    
    Usage:
        @router.get("/admin/users")
        @require_role("admin", "system")
        async def list_users(user: User = Depends(get_current_user)):
            ...
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' not authorized. Required: {roles}",
            )
        return user
    
    return Depends(role_checker)
