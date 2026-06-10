"""
Diary Endpoints - Patient API
==============================

Endpoints for patient diary entry management:
- GET /: Get all diary entries
- GET /{year}/{month}: Get entries by month
- POST /: Create new diary entry
- PATCH /{entry_uuid}: Update diary entry
- PATCH /{entry_uuid}/delete: Soft delete entry
"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.deps import get_patient_db
from services import DiaryService
from core.logging import get_logger
from core.exceptions import NotFoundError, ValidationError
from core import settings

logger = get_logger(__name__)

router = APIRouter()

# Local dev mode test patient UUID
LOCAL_DEV_PATIENT_UUID = "11111111-1111-1111-1111-111111111111"

def get_patient_uuid_with_fallback(patient_uuid: Optional[str]) -> str:
    """Get patient UUID, falling back to test UUID in local dev mode."""
    if patient_uuid:
        return patient_uuid
    if settings.local_dev_mode:
        return LOCAL_DEV_PATIENT_UUID
    # For local testing without LOCAL_DEV_MODE set, still use fallback
    # This ensures backward compatibility during development
    return LOCAL_DEV_PATIENT_UUID


# =============================================================================
# Request/Response Schemas
# =============================================================================

class DiaryEntrySchema(BaseModel):
    """Response model for diary entry."""
    id: int
    created_at: datetime
    last_updated_at: datetime
    patient_uuid: str
    title: Optional[str] = None
    diary_entry: str
    entry_uuid: str
    marked_for_doctor: bool
    is_deleted: bool

    class Config:
        from_attributes = True


class DiaryEntryCreate(BaseModel):
    """Request model for creating diary entry."""
    title: Optional[str] = None
    diary_entry: str
    marked_for_doctor: bool = False


class DiaryEntryUpdate(BaseModel):
    """Request model for updating diary entry."""
    title: Optional[str] = None
    diary_entry: Optional[str] = None
    marked_for_doctor: Optional[bool] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=List[DiaryEntrySchema],
    summary="Get all diary entries",
    description="Get all diary entries for the patient."
)
async def get_all_diary_entries(
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone"),
):
    """
    Get all diary entries for the authenticated patient.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    logger.info(f"Get all diary entries: patient={patient_uuid}")
    
    diary_service = DiaryService(db)
    entries = diary_service.get_all_entries(UUID(patient_uuid), timezone)
    
    return [DiaryEntrySchema(**e) for e in entries]


@router.get(
    "/{year}/{month}",
    response_model=List[DiaryEntrySchema],
    summary="Get diary entries by month",
    description="Get diary entries for a specific month."
)
async def get_diary_entries_by_month(
    year: int,
    month: int,
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone"),
):
    """
    Get all diary entries for a specific month and year.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12",
        )
    
    logger.info(f"Get diary by month: patient={patient_uuid} {year}/{month}")
    
    diary_service = DiaryService(db)
    
    try:
        entries = diary_service.get_entries_by_month(UUID(patient_uuid), year, month, timezone)
        return [DiaryEntrySchema(**e) for e in entries]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/",
    response_model=DiaryEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create diary entry",
    description="Create a new diary entry."
)
async def create_diary_entry(
    entry_data: DiaryEntryCreate,
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
):
    """
    Create a new diary entry for the authenticated patient.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    logger.info(f"Create diary entry: patient={patient_uuid}")
    
    diary_service = DiaryService(db)
    
    try:
        result = diary_service.create_entry(
            patient_uuid=UUID(patient_uuid),
            diary_entry=entry_data.diary_entry,
            title=entry_data.title,
            marked_for_doctor=entry_data.marked_for_doctor,
        )
        return DiaryEntrySchema(**result)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{entry_uuid}",
    response_model=DiaryEntrySchema,
    summary="Update diary entry",
    description="Update an existing diary entry."
)
async def update_diary_entry(
    entry_uuid: str,
    update_data: DiaryEntryUpdate,
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone"),
):
    """
    Update a diary entry for the authenticated patient.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    logger.info(f"Update diary entry: entry={entry_uuid} patient={patient_uuid}")
    
    diary_service = DiaryService(db)
    
    try:
        result = diary_service.update_entry(
            entry_uuid=UUID(entry_uuid),
            patient_uuid=UUID(patient_uuid),
            title=update_data.title,
            diary_entry=update_data.diary_entry,
            marked_for_doctor=update_data.marked_for_doctor,
            timezone=timezone,
        )
        return DiaryEntrySchema(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{entry_uuid}/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete diary entry",
    description="Soft delete a diary entry by setting is_deleted to true."
)
async def soft_delete_diary_entry(
    entry_uuid: str,
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
):
    """
    Soft deletes a diary entry by setting its is_deleted flag.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    logger.info(f"Delete diary entry: entry={entry_uuid} patient={patient_uuid}")
    
    diary_service = DiaryService(db)
    
    try:
        diary_service.soft_delete_entry(UUID(entry_uuid), UUID(patient_uuid))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/for-doctor",
    response_model=List[DiaryEntrySchema],
    summary="Get entries for doctor",
    description="Get entries marked for doctor review."
)
async def get_entries_for_doctor(
    db: Session = Depends(get_patient_db),
    patient_uuid: Optional[str] = Query(default=None, description="Patient UUID"),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone"),
):
    """
    Get entries marked for doctor review.
    """
    patient_uuid = get_patient_uuid_with_fallback(patient_uuid)
    logger.info(f"Get entries for doctor: patient={patient_uuid}")
    
    diary_service = DiaryService(db)
    entries = diary_service.get_entries_for_doctor(UUID(patient_uuid), timezone)
    
    return [DiaryEntrySchema(**e) for e in entries]
