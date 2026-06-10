"""
================================================================================
Dashboard Endpoints - Doctor API
================================================================================

Module:         dashboard.py
Description:    REST API endpoints for the clinical monitoring dashboard.
                Provides patient ranking, symptom timelines, and weekly reports.

Created:        2025-12-25
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Endpoints:
    GET  /dashboard                          - Landing view with ranked patients
    GET  /dashboard/patient/{uuid}           - Patient detail with timeline
    GET  /dashboard/patient/{uuid}/questions - Patient's shared questions
    GET  /dashboard/reports                  - List weekly reports
    GET  /dashboard/reports/weekly           - Get/generate weekly report
    POST /dashboard/reports/generate         - Trigger report generation

Security:
    - All endpoints require authentication
    - Physician-scoped data access
    - Staff access via associated physicians
    - Audit logging on all patient data access

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_patient_db_session, get_doctor_db_session, TokenData
from services.dashboard_service import DashboardService
from services.audit_service import AuditService
from core.logging import get_logger
from core.exceptions import NotFoundError, AuthorizationError

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class PatientRankingSummary(BaseModel):
    """Summary of a patient for the dashboard ranking."""
    patient_uuid: str
    first_name: Optional[str]
    last_name: Optional[str]
    email_address: Optional[str]
    last_checkin: Optional[str]
    max_severity: Optional[str]
    has_escalation: bool
    severity_badge: str

    class Config:
        from_attributes = True


class DashboardLandingResponse(BaseModel):
    """Response for dashboard landing view."""
    patients: List[PatientRankingSummary]
    total_patients: int
    period_days: int


class SymptomDataPoint(BaseModel):
    """A single data point in the symptom timeline."""
    date: Optional[str]
    severity: str
    severity_numeric: int


class TreatmentEventResponse(BaseModel):
    """A treatment event for timeline overlay."""
    event_type: str
    event_date: Optional[str]
    metadata: dict = {}


class PatientTimelineResponse(BaseModel):
    """Response for patient symptom timeline."""
    patient_uuid: str
    period_days: int
    symptom_series: dict  # symptom_id -> list of data points
    treatment_events: List[TreatmentEventResponse]


class SharedQuestionResponse(BaseModel):
    """A shared patient question."""
    id: str
    question_text: str
    category: Optional[str]
    is_answered: bool
    created_at: Optional[str]


class WeeklyReportSummary(BaseModel):
    """Summary of a weekly report."""
    report_id: Optional[str]
    physician_id: str
    report_week_start: str
    report_week_end: str
    generated_at: str
    patient_count: int
    total_alerts: int
    total_questions: int


class PatientReportSection(BaseModel):
    """Patient section in weekly report."""
    patient: dict
    symptoms: dict
    alerts: List[dict]
    questions: List[dict]


class WeeklyReportDataResponse(BaseModel):
    """Full weekly report data."""
    physician_id: str
    report_week_start: str
    report_week_end: str
    generated_at: str
    patient_count: int
    total_alerts: int
    total_questions: int
    patients: List[PatientReportSection]


# =============================================================================
# Dashboard Landing
# =============================================================================

@router.get(
    "",
    response_model=DashboardLandingResponse,
    summary="Dashboard Landing",
    description="Get ranked list of patients requiring attention.",
)
async def get_dashboard_landing(
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum patients"),
    request: Request = None,
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get the dashboard landing view with ranked patients.
    
    Patients are ranked by:
    1. Has urgent escalation (highest priority)
    2. Maximum symptom severity
    3. Most recent activity
    
    This answers: "Which patients need attention right now?"
    """
    logger.info(f"Dashboard landing for user {current_user.sub}")
    
    dashboard_service = DashboardService(patient_db, doctor_db)
    
    try:
        patients = dashboard_service.get_ranked_patient_list(
            physician_id=UUID(current_user.sub),
            days=days,
            limit=limit,
        )
        
        # Log the dashboard access for audit
        audit_service = AuditService(doctor_db)
        audit_service.log_action(
            user_id=UUID(current_user.sub),
            user_role="physician",
            action="view_dashboard",
            entity_type="dashboard",
            ip_address=request.client.host if request else None,
        )
        
        return DashboardLandingResponse(
            patients=[PatientRankingSummary(**p) for p in patients],
            total_patients=len(patients),
            period_days=days,
        )
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard",
        )


# =============================================================================
# Patient Detail View
# =============================================================================

@router.get(
    "/patient/{patient_uuid}",
    response_model=PatientTimelineResponse,
    summary="Patient Symptom Timeline",
    description="Get symptom timeline for a specific patient.",
)
async def get_patient_timeline(
    patient_uuid: UUID,
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    request: Request = None,
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get symptom timeline data for a patient.
    
    Returns data for multi-line time series chart:
    - Each symptom type = one line
    - Severity mapped to numeric scale (1=mild, 4=urgent)
    - Treatment events as vertical reference lines
    """
    logger.info(f"Getting timeline for patient {patient_uuid}")
    
    dashboard_service = DashboardService(patient_db, doctor_db)
    
    try:
        timeline = dashboard_service.get_patient_symptom_timeline(
            patient_uuid=patient_uuid,
            physician_id=UUID(current_user.sub),
            days=days,
        )
        
        # Log access
        audit_service = AuditService(doctor_db)
        audit_service.log_action(
            user_id=UUID(current_user.sub),
            user_role="physician",
            action="view_patient_timeline",
            entity_type="patient",
            entity_id=patient_uuid,
            ip_address=request.client.host if request else None,
        )
        
        return PatientTimelineResponse(
            patient_uuid=timeline["patient_uuid"],
            period_days=timeline["period_days"],
            symptom_series=timeline["symptom_series"],
            treatment_events=[
                TreatmentEventResponse(**e) for e in timeline["treatment_events"]
            ],
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting patient timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load patient timeline",
        )


# =============================================================================
# Patient Questions
# =============================================================================

@router.get(
    "/patient/{patient_uuid}/questions",
    response_model=List[SharedQuestionResponse],
    summary="Patient Shared Questions",
    description="Get questions shared by the patient.",
)
async def get_patient_questions(
    patient_uuid: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get questions the patient has chosen to share with their physician.
    
    Only returns questions where share_with_physician = true.
    Private questions are never visible to physicians.
    """
    logger.info(f"Getting shared questions for patient {patient_uuid}")
    
    dashboard_service = DashboardService(patient_db, doctor_db)
    
    try:
        questions = dashboard_service.get_patient_shared_questions(
            patient_uuid=patient_uuid,
            physician_id=UUID(current_user.sub),
            limit=limit,
        )
        
        return [SharedQuestionResponse(**q) for q in questions]
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# =============================================================================
# Weekly Reports
# =============================================================================

@router.get(
    "/reports/weekly",
    response_model=WeeklyReportDataResponse,
    summary="Get Weekly Report Data",
    description="Get data for the weekly physician report.",
)
async def get_weekly_report(
    week_start: Optional[date] = Query(None, description="Report week start (default: last Monday)"),
    current_user: TokenData = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db_session),
    doctor_db: Session = Depends(get_doctor_db_session),
):
    """
    Get data for a weekly physician report.
    
    Includes:
    - Patient demographics
    - Weekly symptom severity trends
    - Escalation events
    - Shared questions
    - Treatment overlays
    """
    logger.info(f"Getting weekly report for physician {current_user.sub}")
    
    dashboard_service = DashboardService(patient_db, doctor_db)
    
    try:
        report_data = dashboard_service.get_weekly_report_data(
            physician_id=UUID(current_user.sub),
            week_start=week_start,
        )
        
        return WeeklyReportDataResponse(
            physician_id=report_data["physician_id"],
            report_week_start=report_data["report_week_start"],
            report_week_end=report_data["report_week_end"],
            generated_at=report_data["generated_at"],
            patient_count=report_data["patient_count"],
            total_alerts=report_data["total_alerts"],
            total_questions=report_data["total_questions"],
            patients=[
                PatientReportSection(
                    patient=p["patient"],
                    symptoms=p["symptoms"],
                    alerts=p["alerts"],
                    questions=p["questions"],
                )
                for p in report_data["patients"]
            ],
        )
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate weekly report",
        )



