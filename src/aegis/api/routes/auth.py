"""
Authentication Routes

Login, token refresh, and user management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from aegis.api.auth import (
    LoginRequest,
    TokenResponse,
    User,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_settings,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserResponse(BaseModel):
    """User information response."""
    id: str
    email: str
    tenant_id: str
    roles: list[str]
    full_name: str | None


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate and get access token.
    
    **Demo Credentials:**
    - admin@aegis.health / admin123 (admin role)
    - user@aegis.health / user123 (user role)
    - analyst@hospital-a.com / analyst123 (analyst role, tenant: hospital_a)
    """
    user = authenticate_user(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings().auth
    access_token = create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        tenant_id=current_user.tenant_id,
        roles=current_user.roles,
        full_name=current_user.full_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
):
    """Refresh access token."""
    settings = get_settings().auth
    access_token = create_access_token(current_user)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
