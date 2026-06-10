"""
Chemo Endpoints - Patient API
==============================

Endpoints for chemotherapy date management:
- POST /log: Log a new chemo date
- GET /history: Get chemo history
- GET /month/{year}/{month}: Get chemo by month
- GET /upcoming: Get upcoming chemo dates
- DELETE /{date}: Delete a chemo date
"""

from uuid import UUID
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.deps import get_patient_db
from services import ChemoService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class LogChemoDateRequest(BaseModel):
    """Request model for logging chemo date."""
    chemo_date: date
    timezone: Optional[str] = "America/Los_Angeles"


class LogChemoDateResponse(BaseModel):
    """Response model for logged chemo date."""
    success: bool
    message: str
    chemo_date: date

    class Config:
        from_attributes = True


class ChemoDateItem(BaseModel):
    """Single chemo date item."""
    id: int
    chemo_date: date
    created_at: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/log",
    response_model=LogChemoDateResponse,
    summary="Log chemo date",
    description="Log a chemotherapy date for the patient."
)
def log_chemo_date(
    request: LogChemoDateRequest,
    db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Log a new chemotherapy date for the authenticated patient.
    """
    logger.info(f"Log chemo: patient={patient_uuid} date={request.chemo_date}")
    
    chemo_service = ChemoService(db)
    
    try:
        result = chemo_service.log_chemo_date(
            patient_uuid=UUID(patient_uuid),
            chemo_date=request.chemo_date,
            timezone=request.timezone,
        )
        
        return LogChemoDateResponse(
            success=result["success"],
            message=result["message"],
            chemo_date=result["chemo_date"],
        )
    except Exception as e:
        logger.error(f"Log chemo failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=List[ChemoDateItem],
    summary="Get chemo history",
    description="Get all chemotherapy dates for the patient."
)
def get_chemo_history(
    db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
    limit: int = Query(default=100, le=500),
):
    """
    Get chemotherapy history for the patient.
    """
    logger.info(f"Get chemo history: patient={patient_uuid}")
    
    chemo_service = ChemoService(db)
    entries = chemo_service.get_chemo_history(UUID(patient_uuid), limit)
    
    return [
        ChemoDateItem(
            id=e["id"],
            chemo_date=e["chemo_date"],
            created_at=e["created_at"].isoformat() if e.get("created_at") else None,
        )
        for e in entries
    ]


@router.get(
    "/month/{year}/{month}",
    response_model=List[ChemoDateItem],
    summary="Get chemo by month",
    description="Get chemotherapy dates for a specific month."
)
def get_chemo_by_month(
    year: int,
    month: int,
    db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Get chemo dates for a specific month.
    """
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12",
        )
    
    logger.info(f"Get chemo by month: patient={patient_uuid} {year}/{month}")
    
    chemo_service = ChemoService(db)
    entries = chemo_service.get_chemo_by_month(UUID(patient_uuid), year, month)
    
    return [
        ChemoDateItem(
            id=e["id"],
            chemo_date=e["chemo_date"],
            created_at=e["created_at"].isoformat() if e.get("created_at") else None,
        )
        for e in entries
    ]


@router.get(
    "/upcoming",
    response_model=List[ChemoDateItem],
    summary="Get upcoming chemo",
    description="Get upcoming chemotherapy dates."
)
def get_upcoming_chemo(
    db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
    limit: int = Query(default=10, le=50),
):
    """
    Get upcoming chemo dates from today onwards.
    """
    logger.info(f"Get upcoming chemo: patient={patient_uuid}")
    
    chemo_service = ChemoService(db)
    entries = chemo_service.get_upcoming_chemo(UUID(patient_uuid), limit=limit)
    
    return [
        ChemoDateItem(
            id=e["id"],
            chemo_date=e["chemo_date"],
            created_at=e["created_at"].isoformat() if e.get("created_at") else None,
        )
        for e in entries
    ]


@router.delete(
    "/{chemo_date}",
    summary="Delete chemo date",
    description="Delete a chemotherapy date entry."
)
def delete_chemo_date(
    chemo_date: date,
    db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Delete a chemo date entry.
    """
    logger.info(f"Delete chemo: patient={patient_uuid} date={chemo_date}")
    
    chemo_service = ChemoService(db)
    result = chemo_service.delete_chemo_date(UUID(patient_uuid), chemo_date)
    
    return result





