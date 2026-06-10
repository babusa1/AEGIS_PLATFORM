"""
Authentication Endpoints - Doctor API
=====================================

Complete authentication endpoints using AWS Cognito:
- POST /signup: Register new staff member
- POST /login: Authenticate with email/password
- POST /complete-new-password: Complete password setup
- POST /logout: Logout (client-side token removal)
- DELETE /delete-user: Delete staff account

Rate Limiting:
- Login: 5 attempts per minute (prevents brute force)
- Signup: 5 attempts per minute
- Password reset: 3 attempts per minute
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from api.deps import get_doctor_db_session, get_patient_db_session
from services import AuthService
from core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from core.logging import get_logger
from core.middleware.rate_limiting import limiter, AUTH_RATE_LIMIT, PASSWORD_RESET_LIMIT

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class SignupRequest(BaseModel):
    """Signup request for new staff member."""
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "staff"  # staff, physician, admin
    clinic_uuid: Optional[str] = None


class SignupResponse(BaseModel):
    """Signup response."""
    message: str
    email: str
    user_status: str


class LoginRequest(BaseModel):
    """Login request with email and password."""
    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    """JWT tokens returned after successful authentication."""
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str = "Bearer"


class LoginResponse(BaseModel):
    """Login response with success status and optional tokens."""
    valid: bool
    message: str
    user_status: Optional[str] = None
    session: Optional[str] = None
    tokens: Optional[AuthTokens] = None


class CompletePasswordRequest(BaseModel):
    """Request to complete new password setup."""
    email: EmailStr
    new_password: str
    session: str


class CompletePasswordResponse(BaseModel):
    """Response after setting new password."""
    message: str
    tokens: AuthTokens


class DeleteUserRequest(BaseModel):
    """Request to delete a user."""
    email: Optional[str] = None
    uuid: Optional[str] = None
    skip_aws: bool = False


class LogoutResponse(BaseModel):
    """Logout response."""
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/signup",
    response_model=SignupResponse,
    summary="Register new staff member",
    description="Create a new staff member in AWS Cognito and local database.",
)
@limiter.limit(AUTH_RATE_LIMIT)
async def signup_user(
    request: SignupRequest,
    http_request: Request,
    db: Session = Depends(get_doctor_db_session),
):
    """
    Create a new staff member account.
    
    Creates the user in:
    1. AWS Cognito (authentication)
    2. Local database (staff profile)
    
    A temporary password will be sent to the user's email.
    """
    logger.info(f"Signup request: email={request.email} role={request.role}")
    
    auth_service = AuthService(db)
    
    try:
        result = auth_service.signup(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            role=request.role,
            clinic_uuid=request.clinic_uuid,
        )
        
        return SignupResponse(
            message=result["message"],
            email=result["email"],
            user_status=result["user_status"],
        )
        
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Authenticate a user with email and password. Rate limited to prevent brute force.",
)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_doctor_db_session),
):
    """
    Authenticate a user.
    
    Returns JWT tokens on success, or challenge info if password
    change is required (for users with temporary passwords).
    """
    logger.info(f"Login request: email={request.email}")
    
    auth_service = AuthService(db)
    
    try:
        result = auth_service.login(
            email=request.email,
            password=request.password,
        )
        
        response = LoginResponse(
            valid=result["valid"],
            message=result.get("message", ""),
            user_status=result.get("user_status"),
            session=result.get("session"),
        )
        
        if result.get("tokens"):
            response.tokens = AuthTokens(**result["tokens"])
        
        return response
        
    except ExternalServiceError as e:
        logger.error(f"Login failed for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post(
    "/complete-new-password",
    response_model=CompletePasswordResponse,
    summary="Complete Password Setup",
    description="Set a new password for a user with a temporary password.",
)
@limiter.limit(PASSWORD_RESET_LIMIT)
async def complete_new_password(
    request: CompletePasswordRequest,
    http_request: Request,
    db: Session = Depends(get_doctor_db_session),
):
    """
    Complete password setup for users with temporary passwords.
    
    This is called after login returns a FORCE_CHANGE_PASSWORD status.
    The session token from the login response must be provided.
    """
    logger.info(f"Complete new password: email={request.email}")
    
    auth_service = AuthService(db)
    
    try:
        result = auth_service.complete_new_password(
            email=request.email,
            new_password=request.new_password,
            session=request.session,
        )
        
        return CompletePasswordResponse(
            message=result["message"],
            tokens=AuthTokens(**result["tokens"]),
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout",
    description="Logout the current user.",
)
async def logout():
    """
    Logout the current user.
    
    Note: This is primarily a client-side operation. The client
    should delete the stored tokens. This endpoint provides a
    consistent API response.
    """
    logger.info("Logout request")
    return LogoutResponse(message="Logout successful")


@router.delete(
    "/delete-user",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user account",
    description="Delete a staff member account and all associated data.",
)
async def delete_user(
    request: DeleteUserRequest,
    db: Session = Depends(get_doctor_db_session),
):
    """
    Delete a staff member account.
    
    Can delete by email or UUID.
    Optionally skips AWS Cognito deletion.
    
    This is an irreversible action.
    """
    logger.warning(f"Delete user request: email={request.email} uuid={request.uuid}")
    
    auth_service = AuthService(db)
    
    try:
        auth_service.delete_user(
            email=request.email,
            uuid=request.uuid,
            skip_aws=request.skip_aws,
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
