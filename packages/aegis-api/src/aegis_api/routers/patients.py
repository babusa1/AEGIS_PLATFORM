"""Patient API Router"""

from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel
import structlog

from aegis_api.security.auth import get_current_user, User

logger = structlog.get_logger(__name__)
router = APIRouter()


class PatientSummary(BaseModel):
    id: str
    mrn: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    birth_date: str | None = None
    gender: str | None = None


@router.get("", response_model=list[PatientSummary])
async def search_patients(
    request: Request,
    q: str | None = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
):
    """Search patients."""
    tenant_id = request.state.tenant_id
    logger.info("Patient search", tenant=tenant_id, user=user.id)
    
    # TODO: Implement with graph queries
    return [
        PatientSummary(
            id="Patient/12345",
            mrn="MRN001",
            given_name="John",
            family_name="Smith",
            birth_date="1980-01-15",
            gender="male",
        )
    ]


@router.get("/{patient_id}", response_model=PatientSummary)
async def get_patient(
    patient_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get patient by ID."""
    return PatientSummary(
        id=patient_id,
        mrn="MRN001",
        given_name="John",
        family_name="Smith",
    )


@router.get("/{patient_id}/360")
async def get_patient_360(
    patient_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get comprehensive Patient 360 view."""
    return {
        "patient": {"id": patient_id},
        "encounters": [],
        "conditions": [],
        "medications": [],
        "observations": [],
        "care_gaps": [],
        "risk_scores": [],
    }
