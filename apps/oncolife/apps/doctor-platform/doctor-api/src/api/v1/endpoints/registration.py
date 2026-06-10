"""
Registration Endpoints - Doctor API
====================================

Admin-controlled physician and staff registration.

Endpoints:
- POST /registration/physician: Admin creates physician (invite sent)
- POST /registration/staff: Physician creates staff (invite sent)
- GET /registration/permissions/{uuid}: Get staff permissions

Security:
- Physicians cannot self-signup
- Only admins create physicians
- Physicians control their staff
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_doctor_db_session, TokenData
from services import RegistrationService, AuditService
from core.logging import get_logger
from core.exceptions import (
    AuthorizationError,
    ConflictError,
    ValidationError,
    NotFoundError,
)

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreatePhysicianRequest(BaseModel):
    """Request to create a physician (admin only)."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    npi_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    clinic_uuid: UUID


class CreateStaffRequest(BaseModel):
    """Request to create a staff member (physician only)."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern=r"^(nurse|ma|navigator)$")


class RegistrationResponse(BaseModel):
    """Response after registration."""
    success: bool
    message: str
    user_uuid: str
    email: str
    role: str
    invite_sent: bool
    status: str


class PermissionsResponse(BaseModel):
    """Response for staff permissions."""
    role: str
    physician_uuid: str
    can_view_dashboard: bool
    can_view_patients: bool
    can_flag_concerns: bool
    can_review_questions: bool
    can_reassign_patients: bool
    can_modify_records: bool
    can_create_staff: bool
    can_generate_reports: bool
    patient_scope: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/physician",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Physician (Admin Only)",
    description="Admin-initiated physician registration. Sends invite email.",
)
async def create_physician(
    request: CreatePhysicianRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Create a new physician account.
    
    ADMIN ONLY - Physicians cannot self-signup.
    
    Flow:
    1. Verify admin permission
    2. Create physician in database
    3. Create Cognito user (FORCE_CHANGE_PASSWORD)
    4. Send invite email with temp password
    5. Log the action
    """
    logger.info(f"Admin {current_user.sub} creating physician: {request.email}")
    
    registration_service = RegistrationService(db)
    
    try:
        result = registration_service.register_physician_by_admin(
            admin_uuid=UUID(current_user.sub),
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            npi_number=request.npi_number,
            clinic_uuid=request.clinic_uuid,
        )
        
        return RegistrationResponse(
            success=result["success"],
            message=result["message"],
            user_uuid=result["physician_uuid"],
            email=result["email"],
            role="physician",
            invite_sent=result["invite_sent"],
            status=result["status"],
        )
        
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/staff",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Staff (Physician Only)",
    description="Physician-controlled staff registration. Sends invite email.",
)
async def create_staff(
    request: CreateStaffRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Create a new staff member account.
    
    PHYSICIAN ONLY - Staff are scoped to the creating physician.
    
    Flow:
    1. Verify requesting user is a physician
    2. Create staff in database (linked to physician)
    3. Create Cognito user (FORCE_CHANGE_PASSWORD)
    4. Send invite email with temp password
    5. Log the action
    """
    logger.info(f"Physician {current_user.sub} creating staff: {request.email}")
    
    registration_service = RegistrationService(db)
    
    try:
        result = registration_service.register_staff_by_physician(
            physician_uuid=UUID(current_user.sub),
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            role=request.role,
        )
        
        return RegistrationResponse(
            success=result["success"],
            message=f"Staff account created for {request.email}",
            user_uuid=result["staff_uuid"],
            email=result["email"],
            role=result["role"],
            invite_sent=result["invite_sent"],
            status=result["status"],
        )
        
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/permissions",
    response_model=PermissionsResponse,
    summary="Get My Permissions",
    description="Get permissions for the current user.",
)
async def get_my_permissions(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Get permissions for the authenticated user.
    
    Returns what actions the user can perform based on their role.
    """
    registration_service = RegistrationService(db)
    
    permissions = registration_service.get_staff_permissions(
        staff_uuid=UUID(current_user.sub)
    )
    
    if "error" in permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return PermissionsResponse(**permissions)


@router.get(
    "/permissions/{staff_uuid}",
    response_model=PermissionsResponse,
    summary="Get Staff Permissions",
    description="Get permissions for a specific staff member.",
)
async def get_staff_permissions(
    staff_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Get permissions for a staff member.
    
    Returns what actions the staff member can perform.
    """
    registration_service = RegistrationService(db)
    
    permissions = registration_service.get_staff_permissions(staff_uuid)
    
    if "error" in permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
    
    return PermissionsResponse(**permissions)



