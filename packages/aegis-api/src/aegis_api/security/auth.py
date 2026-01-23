"""
Authentication utilities.
"""

from dataclasses import dataclass
from typing import Any
from datetime import datetime
import structlog

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


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """
    Get current authenticated user.
    
    In production, this would validate JWT and fetch user details.
    For development, returns a mock user.
    """
    # Development mode - return mock user
    if not credentials:
        # Check for tenant header
        tenant_id = request.headers.get("X-Tenant-ID", "dev-tenant")
        role = request.headers.get("X-Role", "physician")
        
        return User(
            id="dev-user",
            tenant_id=tenant_id,
            role=role,
            email="dev@aegis.local",
            name="Development User",
            permissions=["read", "write"],
        )
    
    # Production - validate JWT
    token = credentials.credentials
    
    try:
        # TODO: Implement JWT validation
        # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # For now, return mock user
        return User(
            id="user-from-token",
            tenant_id="tenant-from-token",
            role="physician",
            email="user@hospital.org",
            name="Authenticated User",
        )
        
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
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
