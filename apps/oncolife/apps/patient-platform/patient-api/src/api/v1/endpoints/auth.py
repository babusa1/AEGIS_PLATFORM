"""
Authentication Endpoints - Patient API
=======================================

Complete authentication endpoints using AWS Cognito:
- POST /signup: Register new user
- POST /login: Authenticate and get tokens
- POST /complete-new-password: Complete password setup
- POST /logout: Client-side logout acknowledgment
- DELETE /delete-patient: Delete patient account

Rate Limiting:
- Login: 5 attempts per minute (prevents brute force)
- Signup: 5 attempts per minute
- Password reset: 3 attempts per minute
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List

from api.deps import get_patient_db, get_doctor_db
from services import AuthService
from core.logging import get_logger
from core.exceptions import (
    ConflictError,
    NotFoundError,
    AuthenticationError,
    ValidationError,
    ExternalServiceError,
)
from core.middleware.rate_limiting import limiter, AUTH_RATE_LIMIT, PASSWORD_RESET_LIMIT

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class SignupRequest(BaseModel):
    """Request model for user signup."""
    email: EmailStr
    first_name: str
    last_name: str
    physician_email: Optional[str] = None


class SignupResponse(BaseModel):
    """Response model for successful signup."""
    message: str
    email: str
    user_status: str


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    """JWT tokens returned on successful authentication."""
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str


class LoginResponse(BaseModel):
    """Response model for login attempt."""
    valid: bool
    message: str
    user_status: Optional[str] = None
    tokens: Optional[AuthTokens] = None
    session: Optional[str] = None


class CompleteNewPasswordRequest(BaseModel):
    """Request model for completing password setup."""
    email: EmailStr
    new_password: str
    session: str


class CompleteNewPasswordResponse(BaseModel):
    """Response model for successful password completion."""
    message: str
    tokens: AuthTokens


class DeletePatientRequest(BaseModel):
    """Request model for patient deletion."""
    email: Optional[str] = None
    uuid: Optional[str] = None
    skip_aws: bool = False


class LogoutResponse(BaseModel):
    """Response model for logout."""
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/signup",
    response_model=SignupResponse,
    summary="Register new user",
    description="Create a new user in AWS Cognito and local database."
)
@limiter.limit(AUTH_RATE_LIMIT)
async def signup_user(
    request: SignupRequest,
    http_request: Request,
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
) -> SignupResponse:
    """
    Create a new user account.
    
    Creates the user in:
    1. AWS Cognito (authentication)
    2. Local database (patient info & config)
    3. Physician association
    
    A temporary password will be sent to the user's email.
    """
    logger.info(f"Signup request: email={request.email}")
    
    auth_service = AuthService(patient_db, doctor_db)
    
    try:
        result = auth_service.signup(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            physician_email=request.physician_email,
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and return JWT tokens. Rate limited to prevent brute force."
)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: LoginRequest,
    http_request: Request,
    patient_db: Session = Depends(get_patient_db),
) -> LoginResponse:
    """
    Authenticate a user and return tokens.
    
    If a temporary password is used, returns a session token
    for the password change flow.
    """
    logger.info(f"Login request: email={request.email}")
    
    auth_service = AuthService(patient_db)
    
    try:
        result = auth_service.login(
            email=request.email,
            password=request.password,
        )
        
        tokens = None
        if result.get("tokens"):
            tokens = AuthTokens(**result["tokens"])
        
        return LoginResponse(
            valid=result["valid"],
            message=result["message"],
            user_status=result.get("user_status"),
            tokens=tokens,
            session=result.get("session"),
        )
        
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/complete-new-password",
    response_model=CompleteNewPasswordResponse,
    summary="Complete password setup",
    description="Complete new password setup for users with temporary passwords."
)
@limiter.limit(PASSWORD_RESET_LIMIT)
async def complete_new_password(
    request: CompleteNewPasswordRequest,
    http_request: Request,
    patient_db: Session = Depends(get_patient_db),
) -> CompleteNewPasswordResponse:
    """
    Complete the new password setup for a user who was
    created with a temporary password.
    """
    logger.info(f"Complete new password: email={request.email}")
    
    auth_service = AuthService(patient_db)
    
    try:
        result = auth_service.complete_new_password(
            email=request.email,
            new_password=request.new_password,
            session=request.session,
        )
        
        return CompleteNewPasswordResponse(
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout user",
    description="Client-side logout acknowledgment."
)
async def logout() -> LogoutResponse:
    """
    Client-side logout.
    
    The real action is the client deleting the token.
    This endpoint is a formality for logging.
    """
    logger.info("Logout request")
    
    auth_service = AuthService(None)  # No DB needed
    result = auth_service.logout()
    
    return LogoutResponse(message=result["message"])


@router.delete(
    "/delete-patient",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient account",
    description="Soft delete patient account and all associated data."
)
async def delete_patient(
    request: DeletePatientRequest,
    patient_db: Session = Depends(get_patient_db),
) -> None:
    """
    Delete all data for the specified user.
    
    Can delete by email or UUID.
    Optionally skips AWS Cognito deletion.
    
    This is an irreversible action.
    """
    logger.warning(f"Delete patient request: email={request.email} uuid={request.uuid}")
    
    auth_service = AuthService(patient_db)
    
    try:
        auth_service.delete_patient(
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


@router.get(
    "/me",
    summary="Get current user",
    description="Get current authenticated user info from token."
)
async def get_me(
    # current_user = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """
    Get current authenticated user info.
    """
    # Placeholder - enable with proper auth dependency
    return {
        "message": "Use Cognito token to get user info",
        "hint": "Pass Authorization: Bearer <token> header"
    }
