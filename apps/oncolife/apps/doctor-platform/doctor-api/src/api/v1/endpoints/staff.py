"""
Staff Endpoints - Doctor API
============================

Handles staff and physician management operations.

Endpoints:
- GET /staff: List all staff members
- GET /staff/{staff_uuid}: Get a specific staff member
- POST /staff/physician: Create a new physician
- POST /staff/member: Create a new staff member
- GET /staff/physicians: List all physicians
- GET /staff/for-physician/{physician_uuid}: Get staff for a physician
- GET /staff/search: Search staff by name

All endpoints require authentication.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_doctor_db_session, TokenData
from services import StaffService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class StaffResponse(BaseModel):
    """Staff member information response."""
    staff_uuid: str
    email_address: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    role: str
    npi_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class CreatePhysicianRequest(BaseModel):
    """Request to create a new physician."""
    email_address: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    npi_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    clinic_uuid: UUID


class CreateStaffRequest(BaseModel):
    """Request to create a new staff member."""
    email_address: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern=r"^(staff|admin)$")
    physician_uuids: List[UUID] = Field(..., min_items=1)
    clinic_uuid: UUID


class StaffListResponse(BaseModel):
    """Paginated list of staff members."""
    staff: List[StaffResponse]
    total: int
    skip: int
    limit: int


class ClinicAssociationResponse(BaseModel):
    """Response with physician's clinic association."""
    physician_uuid: str
    clinic_uuid: str


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    staff_uuid: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=StaffListResponse,
    summary="List Staff",
    description="Get a paginated list of all staff members.",
)
async def list_staff(
    role: Optional[str] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get all staff members with optional role filter."""
    staff_service = StaffService(db)
    
    staff_list, total_count = staff_service.list_staff_with_count(
        role=role, skip=skip, limit=limit
    )
    
    return StaffListResponse(
        staff=[StaffResponse(**s.to_dict()) for s in staff_list],
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=List[StaffResponse],
    summary="Search Staff",
    description="Search staff members by name.",
)
async def search_staff(
    q: str = Query(..., min_length=2, description="Search term"),
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Search staff by name (case-insensitive partial match)."""
    staff_service = StaffService(db)
    
    staff_list = staff_service.search_staff(
        search_term=q,
        role=role,
        limit=limit,
    )
    
    return [StaffResponse(**s.to_dict()) for s in staff_list]


@router.get(
    "/physicians",
    response_model=List[StaffResponse],
    summary="List Physicians",
    description="Get all physicians.",
)
async def list_physicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get all physician profiles."""
    staff_service = StaffService(db)
    
    physicians = staff_service.list_physicians(skip=skip, limit=limit)
    
    return [StaffResponse(**p.to_dict()) for p in physicians]


@router.get(
    "/for-physician/{physician_uuid}",
    response_model=List[StaffResponse],
    summary="Get Staff for Physician",
    description="Get all staff members associated with a physician.",
)
async def get_staff_for_physician(
    physician_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get staff members working with a specific physician."""
    staff_service = StaffService(db)
    
    staff_list = staff_service.get_staff_for_physician(physician_uuid)
    
    return [StaffResponse(**s.to_dict()) for s in staff_list]


@router.get(
    "/clinic-from-physician/{physician_uuid}",
    response_model=ClinicAssociationResponse,
    summary="Get Clinic for Physician",
    description="Get the clinic associated with a physician.",
)
async def get_clinic_from_physician(
    physician_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get the clinic UUID for a physician."""
    staff_service = StaffService(db)
    
    clinic_uuid = staff_service.get_clinic_for_physician(physician_uuid)
    
    if not clinic_uuid:
        from core.exceptions import NotFoundError
        raise NotFoundError(
            message="No clinic association found for this physician",
            resource_type="ClinicAssociation",
            resource_id=str(physician_uuid),
        )
    
    return ClinicAssociationResponse(
        physician_uuid=str(physician_uuid),
        clinic_uuid=str(clinic_uuid),
    )


@router.get(
    "/{staff_uuid}",
    response_model=StaffResponse,
    summary="Get Staff Member",
    description="Get a specific staff member by UUID.",
)
async def get_staff(
    staff_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get a staff member by their UUID."""
    staff_service = StaffService(db)
    
    staff = staff_service.get_staff_by_uuid(staff_uuid)
    
    return StaffResponse(**staff.to_dict())


@router.post(
    "/physician",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Physician",
    description="Create a new physician profile.",
)
async def add_physician(
    request: CreatePhysicianRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Create a new physician.
    
    Creates the profile and sets up self-association with the clinic.
    """
    staff_service = StaffService(db)
    
    physician = staff_service.create_physician(
        email_address=request.email_address,
        first_name=request.first_name,
        last_name=request.last_name,
        npi_number=request.npi_number,
        clinic_uuid=request.clinic_uuid,
    )
    
    return MessageResponse(
        message="Physician added successfully",
        staff_uuid=str(physician.staff_uuid),
    )


@router.post(
    "/member",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Staff Member",
    description="Create a new staff or admin member.",
)
async def add_staff(
    request: CreateStaffRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """
    Create a new staff member.
    
    Creates the profile and sets up associations with physicians.
    """
    staff_service = StaffService(db)
    
    staff = staff_service.create_staff_member(
        email_address=request.email_address,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role,
        physician_uuids=request.physician_uuids,
        clinic_uuid=request.clinic_uuid,
    )
    
    return MessageResponse(
        message=f"{request.role.capitalize()} added successfully",
        staff_uuid=str(staff.staff_uuid),
    )





