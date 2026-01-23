"""Encounter API Router"""

from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel
import structlog

from aegis_api.security.auth import get_current_user, User

logger = structlog.get_logger(__name__)
router = APIRouter()


class EncounterSummary(BaseModel):
    id: str
    patient_id: str
    status: str
    encounter_class: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.get("", response_model=list[EncounterSummary])
async def search_encounters(
    request: Request,
    patient_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
):
    """Search encounters."""
    return []


@router.get("/{encounter_id}")
async def get_encounter(
    encounter_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get encounter detail."""
    return {
        "encounter": {
            "id": encounter_id,
            "patient_id": "Patient/12345",
            "status": "finished",
        },
        "diagnoses": [],
        "procedures": [],
        "providers": [],
    }
