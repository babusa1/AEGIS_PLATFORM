"""
Authentication Module

JWT-based authentication for the VeritOS API.
Supports local JWT and AWS Cognito.
"""

from datetime import datetime, timedelta
from typing import Annotated
import hashlib

import structlog
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from aegis.config import get_settings

logger = structlog.get_logger(__name__)


# Simple password hashing (for demo - use bcrypt in production)
def _hash_password(password: str) -> str:
    """Hash password using SHA256 (demo only - use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return _hash_password(password) == hashed

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token", auto_error=False)


# =============================================================================
# Models
# =============================================================================

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    tenant_id: str
    roles: list[str] = Field(default_factory=list)
    exp: datetime | None = None
    iat: datetime | None = None


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True
    full_name: str | None = None


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str


# =============================================================================
# In-Memory User Store (for development)
# =============================================================================

# Demo users for local development
DEMO_USERS = {
    "admin@aegis.health": {
        "id": "user-001",
        "email": "admin@aegis.health",
        "password_hash": _hash_password("admin123"),
        "tenant_id": "default",
        "roles": ["admin", "user"],
        "full_name": "VeritOS Admin",
    },
    "user@aegis.health": {
        "id": "user-002",
        "email": "user@aegis.health",
        "password_hash": _hash_password("user123"),
        "tenant_id": "default",
        "roles": ["user"],
        "full_name": "Demo User",
    },
    "analyst@hospital-a.com": {
        "id": "user-003",
        "email": "analyst@hospital-a.com",
        "password_hash": _hash_password("analyst123"),
        "tenant_id": "hospital_a",
        "roles": ["analyst", "user"],
        "full_name": "Hospital A Analyst",
    },
}


# =============================================================================
# Authentication Functions
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return _verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return _hash_password(password)


def authenticate_user(email: str, password: str) -> User | None:
    """
    Authenticate a user by email and password.
    
    Returns User if valid, None otherwise.
    """
    user_data = DEMO_USERS.get(email)
    if not user_data:
        return None
    
    if not verify_password(password, user_data["password_hash"]):
        return None
    
    return User(
        id=user_data["id"],
        email=user_data["email"],
        tenant_id=user_data["tenant_id"],
        roles=user_data["roles"],
        full_name=user_data.get("full_name"),
    )


def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user: The authenticated user
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings().auth
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    payload = {
        "sub": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "roles": user.roles,
        "iat": now,
        "exp": expire,
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    
    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        TokenPayload with decoded data
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings().auth
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        
        return TokenPayload(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id", "default"),
            roles=payload.get("roles", []),
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
            iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None,
        )
        
    except JWTError as e:
        logger.warning("JWT decode error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user": user.email}
    """
    settings = get_settings()
    
    # DEV MODE: Auto-authenticate as admin in development
    if settings.app.env == "development" and bearer is None:
        logger.debug("Dev mode: auto-authenticating as admin")
        return User(
            id="user-001",
            email="admin@aegis.health",
            tenant_id="default",
            roles=["admin", "user"],
            full_name="VeritOS Admin (Dev Mode)",
        )
    
    if bearer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_token(bearer.credentials)
    
    # Look up user (in production, this would query the database)
    for email, user_data in DEMO_USERS.items():
        if user_data["id"] == token_data.sub:
            return User(
                id=user_data["id"],
                email=email,
                tenant_id=user_data["tenant_id"],
                roles=user_data["roles"],
                full_name=user_data.get("full_name"),
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_optional_user(
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> User | None:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for endpoints that work with or without authentication.
    """
    if bearer is None:
        return None
    
    try:
        return await get_current_user(bearer)
    except HTTPException:
        return None


def require_roles(*required_roles: str):
    """
    Dependency factory to require specific roles.
    
    Usage:
        @app.get("/admin-only")
        async def admin_route(user: User = Depends(require_roles("admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        for role in required_roles:
            if role in current_user.roles:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required roles: {', '.join(required_roles)}",
        )
    
    return role_checker


# =============================================================================
# Tenant Context
# =============================================================================

class TenantContext(BaseModel):
    """Context for multi-tenant operations."""
    tenant_id: str
    user_id: str | None = None
    roles: list[str] = Field(default_factory=list)


async def get_tenant_context(
    current_user: User = Depends(get_current_active_user),
) -> TenantContext:
    """
    Get the tenant context from the current user.
    
    This is used to scope all database operations to the user's tenant.
    """
    return TenantContext(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        roles=current_user.roles,
    )


async def get_optional_tenant_context(
    current_user: User | None = Depends(get_optional_user),
) -> TenantContext:
    """
    Get tenant context, defaulting to 'default' if not authenticated.
    """
    if current_user:
        return TenantContext(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            roles=current_user.roles,
        )
    return TenantContext(tenant_id="default")
