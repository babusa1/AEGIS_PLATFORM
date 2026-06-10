"""
Patient Endpoints - Doctor API
==============================

Provides read-only access to patient data for doctors and staff.

Endpoints:
- GET /patients: List patients (for associated physicians)
- GET /patients/{patient_uuid}: Get patient details
- GET /patients/{patient_uuid}/conversations: Get patient's chat history
- GET /patients/{patient_uuid}/alerts: Get patient's symptom alerts
- GET /patients/{patient_uuid}/diary: Get patient's diary entries
- GET /patients/{patient_uuid}/stats: Get patient statistics

All endpoints require authentication and proper authorization.
Access is restricted to patients associated with the requesting
physician/staff member.

Note: This module uses the PatientService for clean separation of concerns.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_patient_db_session, get_doctor_db_session, TokenData
from services import PatientService
from core.logging import get_logger
from core.exceptions import NotFoundError, AuthorizationError

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class PatientSummary(BaseModel):
    """Summary information about a patient."""
    uuid: str
    email_address: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class PatientDetail(BaseModel):
    """Detailed patient information."""
    uuid: str
    email_address: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    disease_type: Optional[str] = None
    treatment_type: Optional[str] = None
    created_at: Optional[str] = None
    mrn: Optional[str] = None

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    """Paginated list of patients."""
    patients: List[PatientSummary]
    total: int
    skip: int
    limit: int


class AlertSummary(BaseModel):
    """Summary of a symptom alert."""
    conversation_uuid: str
    triage_level: str
    symptom_list: Optional[List[str]] = None
    created_at: str
    conversation_state: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Summary of a patient conversation."""
    uuid: str
    created_at: str
    conversation_state: Optional[str] = None
    symptom_list: Optional[List[str]] = None
    overall_feeling: Optional[str] = None
    bulleted_summary: Optional[str] = None

    class Config:
        from_attributes = True


class DiaryEntrySummary(BaseModel):
    """Summary of a diary entry."""
    id: int
    entry_uuid: str
    created_at: str
    title: Optional[str] = None
    diary_entry: str
    marked_for_doctor: bool

    class Config:
        from_attributes = True


class PatientStatistics(BaseModel):
    """Patient statistics."""
    total_conversations: int
    total_alerts: int
    total_diary_entries: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=PatientListResponse,
    summary="List Patients",
    description="Get patients associated with the current physician/staff.",
)
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, min_length=2),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    List patients for the authenticated user.
    
    For physicians: Returns patients directly assigned to them.
    For staff: Returns patients assigned to their associated physicians.
    """
    logger.info(f"Listing patients for user {current_user.sub}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        patients, total = patient_service.get_associated_patients(
            staff_uuid=UUID(current_user.sub),
            search_query=search,
            skip=skip,
            limit=limit,
        )
        
        return PatientListResponse(
            patients=[PatientSummary(**p) for p in patients],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error listing patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patients",
        )


@router.get(
    "/{patient_uuid}",
    response_model=PatientDetail,
    summary="Get Patient Details",
    description="Get detailed information about a specific patient.",
)
async def get_patient(
    patient_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get detailed patient information.
    
    Requires authorization: User must be associated with the patient's
    physician to access their data.
    """
    logger.info(f"Getting patient {patient_uuid} for user {current_user.sub}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        patient = patient_service.get_patient_details(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
        )
        return PatientDetail(**patient)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{patient_uuid}/alerts",
    response_model=List[AlertSummary],
    summary="Get Patient Alerts",
    description="Get symptom alerts for a patient.",
)
async def get_patient_alerts(
    patient_uuid: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get symptom alerts for a patient.
    
    Alerts are conversations with triage levels that require
    care team notification (call_911 or notify_care_team).
    """
    logger.info(f"Getting alerts for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        alerts = patient_service.get_patient_alerts(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
            limit=limit,
        )
        return [AlertSummary(**a) for a in alerts]
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{patient_uuid}/conversations",
    response_model=List[ConversationSummary],
    summary="Get Patient Conversations",
    description="Get chat history for a patient.",
)
async def get_patient_conversations(
    patient_uuid: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get conversation history for a patient.
    
    Returns summaries of symptom checker chat sessions.
    """
    logger.info(f"Getting conversations for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        conversations = patient_service.get_patient_conversations(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
            limit=limit,
        )
        return [ConversationSummary(**c) for c in conversations]
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{patient_uuid}/diary",
    response_model=List[DiaryEntrySummary],
    summary="Get Patient Diary",
    description="Get diary entries for a patient.",
)
async def get_patient_diary(
    patient_uuid: UUID,
    for_doctor_only: bool = Query(False, description="Only entries marked for doctor"),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get diary entries for a patient.
    
    Can filter to only show entries marked for doctor review.
    """
    logger.info(f"Getting diary for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        entries = patient_service.get_patient_diary(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
            for_doctor_only=for_doctor_only,
            limit=limit,
        )
        return [DiaryEntrySummary(**e) for e in entries]
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{patient_uuid}/stats",
    response_model=PatientStatistics,
    summary="Get Patient Statistics",
    description="Get statistics for a patient.",
)
async def get_patient_statistics(
    patient_uuid: UUID,
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get statistics for a patient.
    
    Returns counts of conversations, alerts, and diary entries.
    """
    logger.info(f"Getting statistics for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        stats = patient_service.get_patient_statistics(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
        )
        return PatientStatistics(**stats)
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# =============================================================================
# Patient Questions Endpoint
# =============================================================================

class PatientQuestion(BaseModel):
    """Patient question for doctor review."""
    id: str
    question_text: str
    category: Optional[str] = None
    is_answered: bool = False
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class QuestionsResponse(BaseModel):
    """Response with shared questions."""
    questions: List[PatientQuestion]
    total: int


@router.get(
    "/{patient_uuid}/questions",
    response_model=QuestionsResponse,
    summary="Get Patient Questions",
    description="Get questions shared by the patient for doctor review.",
)
async def get_patient_questions(
    patient_uuid: UUID,
    include_answered: bool = Query(True, description="Include answered questions"),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get shared questions from a patient.
    
    Only questions where share_with_physician=True are visible.
    This allows doctors to see what the patient wants to discuss.
    """
    logger.info(f"Getting shared questions for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        questions = patient_service.get_patient_questions(
            patient_uuid=patient_uuid,
            staff_uuid=UUID(current_user.sub),
            include_answered=include_answered,
            limit=limit,
        )
        return QuestionsResponse(
            questions=[PatientQuestion(**q) for q in questions],
            total=len(questions),
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{patient_uuid}/questions/{question_id}/answered",
    response_model=PatientQuestion,
    summary="Mark Question as Answered",
    description="Mark a patient's question as answered.",
)
async def mark_question_answered(
    patient_uuid: UUID,
    question_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Mark a patient's question as answered.
    
    Doctors can mark questions as answered after discussing with the patient.
    """
    logger.info(f"Marking question {question_id} as answered for patient {patient_uuid}")
    
    patient_service = PatientService(patient_db, doctor_db)
    
    try:
        question = patient_service.mark_question_answered(
            patient_uuid=patient_uuid,
            question_id=question_id,
            staff_uuid=UUID(current_user.sub),
        )
        return PatientQuestion(**question)
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
