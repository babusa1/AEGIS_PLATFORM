"""
Clinic Endpoints - Doctor API
=============================

Handles clinic management operations.

Endpoints:
- GET /clinics: List all clinics
- GET /clinics/{clinic_uuid}: Get a specific clinic
- POST /clinics: Create a new clinic
- PUT /clinics/{clinic_uuid}: Update a clinic
- DELETE /clinics/{clinic_uuid}: Delete a clinic
- GET /clinics/search: Search clinics by name

All endpoints require authentication.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_doctor_db_session, TokenData
from services import ClinicService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ClinicResponse(BaseModel):
    """Clinic information response."""
    uuid: str
    clinic_name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    fax_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class CreateClinicRequest(BaseModel):
    """Request to create a new clinic."""
    clinic_name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    phone_number: Optional[str] = Field(None, max_length=20)
    fax_number: Optional[str] = Field(None, max_length=20)


class UpdateClinicRequest(BaseModel):
    """Request to update a clinic."""
    clinic_name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    phone_number: Optional[str] = Field(None, max_length=20)
    fax_number: Optional[str] = Field(None, max_length=20)


class ClinicListResponse(BaseModel):
    """Paginated list of clinics."""
    clinics: List[ClinicResponse]
    total: int
    skip: int
    limit: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=ClinicListResponse,
    summary="List Clinics",
    description="Get a paginated list of all clinics.",
)
async def list_clinics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get all clinics with pagination."""
    clinic_service = ClinicService(db)
    
    clinics = clinic_service.list_clinics(skip=skip, limit=limit)
    total = clinic_service.count_clinics()
    
    return ClinicListResponse(
        clinics=[ClinicResponse(**c.to_dict()) for c in clinics],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=List[ClinicResponse],
    summary="Search Clinics",
    description="Search clinics by name.",
)
async def search_clinics(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Search clinics by name (case-insensitive partial match)."""
    clinic_service = ClinicService(db)
    
    clinics = clinic_service.search_clinics(search_term=q, limit=limit)
    
    return [ClinicResponse(**c.to_dict()) for c in clinics]


@router.get(
    "/{clinic_uuid}",
    response_model=ClinicResponse,
    summary="Get Clinic",
    description="Get a specific clinic by UUID.",
)
async def get_clinic(
    clinic_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Get a clinic by its UUID."""
    clinic_service = ClinicService(db)
    
    clinic = clinic_service.get_clinic(clinic_uuid)
    
    return ClinicResponse(**clinic.to_dict())


@router.post(
    "",
    response_model=ClinicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Clinic",
    description="Create a new clinic.",
)
async def create_clinic(
    request: CreateClinicRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Create a new clinic."""
    clinic_service = ClinicService(db)
    
    clinic = clinic_service.create_clinic(
        clinic_name=request.clinic_name,
        address=request.address,
        phone_number=request.phone_number,
        fax_number=request.fax_number,
    )
    
    return ClinicResponse(**clinic.to_dict())


@router.put(
    "/{clinic_uuid}",
    response_model=ClinicResponse,
    summary="Update Clinic",
    description="Update an existing clinic.",
)
async def update_clinic(
    clinic_uuid: UUID,
    request: UpdateClinicRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Update a clinic's information."""
    clinic_service = ClinicService(db)
    
    clinic = clinic_service.update_clinic(
        clinic_uuid=clinic_uuid,
        clinic_name=request.clinic_name,
        address=request.address,
        phone_number=request.phone_number,
        fax_number=request.fax_number,
    )
    
    return ClinicResponse(**clinic.to_dict())


@router.delete(
    "/{clinic_uuid}",
    response_model=MessageResponse,
    summary="Delete Clinic",
    description="Delete a clinic.",
)
async def delete_clinic(
    clinic_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_doctor_db_session),
):
    """Delete a clinic by its UUID."""
    clinic_service = ClinicService(db)
    
    clinic_service.delete_clinic(clinic_uuid)
    
    return MessageResponse(message="Clinic deleted successfully")





