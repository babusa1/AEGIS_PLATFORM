"""
Profile Endpoints - Patient API
================================

Endpoints for patient profile management:
- GET /: Get complete patient profile with oncology data
- PUT /: Update complete patient profile
- GET /info: Get detailed patient info
- PATCH /config: Update patient configuration
- PATCH /consent: Update consent status
"""

from uuid import UUID
from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.deps import get_patient_db, get_doctor_db
from services import ProfileService
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class PatientProfileResponse(BaseModel):
    """Complete patient profile response with oncology data."""
    first_name: str
    last_name: str
    email_address: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    reminder_time: Optional[time] = None
    doctor_name: Optional[str] = None
    clinic_name: Optional[str] = None
    # Treatment info
    diagnosis: Optional[str] = None
    treatment_type: Optional[str] = None
    chemo_plan_name: Optional[str] = None
    chemo_start_date: Optional[date] = None
    chemo_end_date: Optional[date] = None
    current_cycle: Optional[int] = None
    total_cycles: Optional[int] = None
    last_chemo_date: Optional[date] = None
    next_physician_visit: Optional[date] = None
    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    """Request model for updating patient profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    reminder_time: Optional[time] = None
    # Treatment info
    diagnosis: Optional[str] = None
    treatment_type: Optional[str] = None
    last_chemo_date: Optional[date] = None
    next_physician_visit: Optional[date] = None
    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class PatientInfoResponse(BaseModel):
    """Detailed patient info response."""
    uuid: str
    created_at: Optional[str] = None
    email_address: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[date] = None
    mrn: Optional[str] = None
    ethnicity: Optional[str] = None
    phone_number: Optional[str] = None
    disease_type: Optional[str] = None
    treatment_type: Optional[str] = None
    is_deleted: bool


class ConfigurationUpdate(BaseModel):
    """Request model for updating configuration."""
    reminder_method: Optional[str] = None
    reminder_time: Optional[time] = None
    acknowledgement_done: Optional[bool] = None
    agreed_conditions: Optional[bool] = None


class ConsentUpdate(BaseModel):
    """Request model for updating consent."""
    acknowledgement_done: Optional[bool] = None
    agreed_conditions: Optional[bool] = None


class ConfigurationResponse(BaseModel):
    """Configuration response."""
    uuid: str
    reminder_method: Optional[str] = None
    reminder_time: Optional[time] = None
    acknowledgement_done: Optional[bool] = None
    agreed_conditions: Optional[bool] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=PatientProfileResponse,
    summary="Get patient profile",
    description="Get complete patient profile with doctor, clinic, and oncology info."
)
async def get_patient_profile(
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Fetch complete patient profile by combining data from
    both patient and doctor databases, including oncology profile.
    """
    logger.info(f"Get profile: patient={patient_uuid}")
    
    profile_service = ProfileService(patient_db, doctor_db)
    
    try:
        profile = profile_service.get_profile(UUID(patient_uuid))
        return PatientProfileResponse(**profile)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/",
    response_model=PatientProfileResponse,
    summary="Update patient profile",
    description="Update patient profile including treatment and emergency contact info."
)
async def update_patient_profile(
    update_data: ProfileUpdateRequest,
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Update patient profile including oncology and emergency contact data.
    """
    logger.info(f"Update profile: patient={patient_uuid}")
    
    profile_service = ProfileService(patient_db, doctor_db)
    
    try:
        profile = profile_service.update_profile(
            patient_uuid=UUID(patient_uuid),
            first_name=update_data.first_name,
            last_name=update_data.last_name,
            phone_number=update_data.phone_number,
            date_of_birth=update_data.date_of_birth,
            reminder_time=update_data.reminder_time,
            diagnosis=update_data.diagnosis,
            treatment_type=update_data.treatment_type,
            last_chemo_date=update_data.last_chemo_date,
            next_physician_visit=update_data.next_physician_visit,
            emergency_contact_name=update_data.emergency_contact_name,
            emergency_contact_phone=update_data.emergency_contact_phone,
        )
        return PatientProfileResponse(**profile)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/info",
    response_model=PatientInfoResponse,
    summary="Get patient info",
    description="Get detailed patient information."
)
async def get_patient_info(
    patient_db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Get detailed patient info.
    """
    logger.info(f"Get patient info: patient={patient_uuid}")
    
    profile_service = ProfileService(patient_db)
    
    try:
        info = profile_service.get_patient_info(UUID(patient_uuid))
        return PatientInfoResponse(**info)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/config",
    response_model=ConfigurationResponse,
    summary="Update configuration",
    description="Update patient configuration settings."
)
async def update_configuration(
    update_data: ConfigurationUpdate,
    patient_db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Update patient configuration.
    """
    logger.info(f"Update config: patient={patient_uuid}")
    
    profile_service = ProfileService(patient_db)
    
    try:
        result = profile_service.update_configuration(
            patient_uuid=UUID(patient_uuid),
            reminder_method=update_data.reminder_method,
            reminder_time=update_data.reminder_time,
            acknowledgement_done=update_data.acknowledgement_done,
            agreed_conditions=update_data.agreed_conditions,
        )
        return ConfigurationResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/consent",
    response_model=ConfigurationResponse,
    summary="Update consent",
    description="Update patient consent status."
)
async def update_consent(
    update_data: ConsentUpdate,
    patient_db: Session = Depends(get_patient_db),
    patient_uuid: str = Query(..., description="Patient UUID"),
):
    """
    Update patient consent status.
    """
    logger.info(f"Update consent: patient={patient_uuid}")
    
    profile_service = ProfileService(patient_db)
    
    try:
        result = profile_service.update_consent(
            patient_uuid=UUID(patient_uuid),
            acknowledgement_done=update_data.acknowledgement_done,
            agreed_conditions=update_data.agreed_conditions,
        )
        return ConfigurationResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
