"""
Education API Endpoints.

Provides endpoints for:
- Post-session education delivery
- Education tab (read-only library)
- Patient summaries
- Education search

All endpoints follow the rule-based, no-AI design.
Education content is clinician-approved and immutable.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_patient_db, get_current_patient_uuid
from services.education_service import EducationService
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SymptomInput(BaseModel):
    """Symptom data from completed session."""
    code: str = Field(..., description="Symptom code (e.g., BLEED-103)")
    name: str = Field(..., description="Symptom name")
    severity: str = Field(..., description="Severity: mild, moderate, urgent")


class MedicationInput(BaseModel):
    """Medication tried during session."""
    name: str = Field(..., description="Medication name")
    effectiveness: str = Field(
        default="none",
        description="Effectiveness: none, partial, helped"
    )


class EducationDeliveryRequest(BaseModel):
    """Request to deliver education after session completion."""
    session_id: UUID = Field(..., description="Symptom session UUID")
    symptom_codes: List[str] = Field(..., description="List of symptom codes")
    severity_levels: dict = Field(..., description="Map of symptom code -> severity")
    escalation: bool = Field(default=False, description="Whether escalation triggered")


class ResourceLink(BaseModel):
    """Link to education resource."""
    title: str
    url: str
    document_id: str
    type: str = "pdf"
    label: Optional[str] = None


class EducationBlock(BaseModel):
    """Education block for a symptom."""
    symptom: str
    symptom_code: str
    severity: Optional[str] = None
    inlineText: str
    inlineTextId: str
    resourceLinks: List[ResourceLink]
    is_care_team_handout: bool = False


class DisclaimerResponse(BaseModel):
    """Mandatory disclaimer."""
    id: str
    text: str


class EducationDeliveryResponse(BaseModel):
    """Response with education content."""
    session_id: str
    educationBlocks: List[EducationBlock]
    disclaimer: DisclaimerResponse
    escalation: bool
    delivered_at: str


class SummaryGenerationRequest(BaseModel):
    """Request to generate patient summary."""
    session_id: UUID
    symptoms: List[SymptomInput]
    medications_tried: List[MedicationInput] = Field(default_factory=list)
    escalation: bool = False


class PatientNoteRequest(BaseModel):
    """Request to add patient note to summary."""
    note: str = Field(..., max_length=300, description="Patient's optional note (max 300 chars)")


class PatientSummaryResponse(BaseModel):
    """Patient summary response."""
    id: str
    session_id: str
    summary_text: str
    patient_note: Optional[str] = None
    escalation: bool
    locked: bool = True
    created_at: str


class EducationDocument(BaseModel):
    """Education document for display."""
    id: str
    symptom_code: Optional[str] = None
    title: str
    inline_text: str
    pdf_url: Optional[str] = None
    version: int
    approved_date: Optional[str] = None


class EducationTabResponse(BaseModel):
    """Education tab content."""
    my_current_symptoms: List[EducationDocument]
    common_symptoms: List[EducationDocument]
    care_team_handouts: List[dict]
    active_symptom_codes: List[str]
    last_updated: str


# =============================================================================
# POST-SESSION EDUCATION DELIVERY
# =============================================================================

@router.post(
    "/deliver",
    response_model=EducationDeliveryResponse,
    summary="Deliver education after session completion",
    description="""
    Triggered when symptom checker session completes (Rule Engine Status = COMPLETED).
    
    Returns:
    - Education blocks for each symptom
    - Care Team Handout (always included)
    - Mandatory disclaimer
    
    All content is clinician-approved, not AI-generated.
    """
)
async def deliver_education(
    request: EducationDeliveryRequest,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Deliver education content after symptom session completion."""
    logger.info(f"Education delivery requested for session: {request.session_id}")
    
    service = EducationService(db)
    
    try:
        result = await service.deliver_post_session_education(
            session_id=request.session_id,
            symptom_codes=request.symptom_codes,
            severity_levels=request.severity_levels,
            escalation=request.escalation,
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except Exception as e:
        logger.error(f"Education delivery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deliver education content",
        )


# =============================================================================
# PATIENT SUMMARY
# =============================================================================

@router.post(
    "/summary",
    response_model=PatientSummaryResponse,
    summary="Generate patient summary",
    description="""
    Generate deterministic summary from templates (not AI).
    
    Template format:
    "You reported {{symptom_list}} with {{severity_list}} severity.
    You tried {{medications_tried}} with {{effectiveness}}.
    {{escalation_sentence}}"
    
    Summary is immutable once generated.
    """
)
async def generate_summary(
    request: SummaryGenerationRequest,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Generate patient summary from template."""
    logger.info(f"Summary generation requested for session: {request.session_id}")
    
    service = EducationService(db)
    
    symptoms = [
        {"code": s.code, "name": s.name, "severity": s.severity}
        for s in request.symptoms
    ]
    
    medications = [
        {"name": m.name, "effectiveness": m.effectiveness}
        for m in request.medications_tried
    ]
    
    try:
        summary = service.generate_patient_summary(
            session_id=request.session_id,
            patient_id=patient_uuid,
            symptoms=symptoms,
            medications_tried=medications,
            escalation=request.escalation,
        )
        
        return PatientSummaryResponse(
            id=str(summary.id),
            session_id=str(summary.session_id),
            summary_text=summary.summary_text,
            patient_note=summary.patient_note,
            escalation=summary.escalation,
            locked=summary.locked,
            created_at=summary.created_at.isoformat(),
        )
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary",
        )


@router.post(
    "/summary/{summary_id}/note",
    response_model=PatientSummaryResponse,
    summary="Add patient note to summary",
    description="""
    Add optional patient note to existing summary.
    Max 300 characters. Does not modify system-generated text.
    """
)
async def add_patient_note(
    summary_id: UUID,
    request: PatientNoteRequest,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Add patient note to summary."""
    service = EducationService(db)
    
    try:
        summary = service.add_patient_note(
            summary_id=summary_id,
            patient_note=request.note,
        )
        
        return PatientSummaryResponse(
            id=str(summary.id),
            session_id=str(summary.session_id),
            summary_text=summary.summary_text,
            patient_note=summary.patient_note,
            escalation=summary.escalation,
            locked=summary.locked,
            created_at=summary.created_at.isoformat(),
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )


@router.get(
    "/summary/{session_id}",
    response_model=PatientSummaryResponse,
    summary="Get summary for session",
)
async def get_summary(
    session_id: UUID,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Get patient summary for a session."""
    from db.models.education import PatientSummary
    
    summary = db.query(PatientSummary).filter(
        PatientSummary.session_id == session_id,
        PatientSummary.patient_id == patient_uuid,
    ).first()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary not found for session {session_id}",
        )
    
    return PatientSummaryResponse(
        id=str(summary.id),
        session_id=str(summary.session_id),
        summary_text=summary.summary_text,
        patient_note=summary.patient_note,
        escalation=summary.escalation,
        locked=summary.locked,
        created_at=summary.created_at.isoformat(),
    )


# =============================================================================
# EDUCATION TAB (Read-Only Library)
# =============================================================================

@router.get(
    "/tab",
    response_model=EducationTabResponse,
    summary="Get education tab content",
    description="""
    Get organized education library content.
    
    Sections:
    1. My Current Symptoms (last 7 days)
    2. Common Chemotherapy Symptoms
    3. Care Team Handouts
    
    Read-only access. No symptom reporting or chat.
    """
)
async def get_education_tab(
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
    limit: int = Query(default=20, le=50),
):
    """Get education tab content for patient."""
    service = EducationService(db)
    
    result = service.get_education_tab_content(
        patient_id=patient_uuid,
        limit=limit,
    )
    
    return result


@router.get(
    "/pdfs",
    summary="Get all education PDFs",
    description="Simple endpoint to get all available education PDFs.",
)
async def get_education_pdfs(
    db: Session = Depends(get_patient_db),
    limit: int = Query(default=50, le=100),
):
    """
    Get all education PDFs.
    
    This endpoint returns all active education PDFs with proper URLs:
    - Development: Local static file URLs (/static/education/...)
    - Production: S3 pre-signed URLs (time-limited, secure)
    
    Works without requiring symptom sessions.
    """
    from sqlalchemy import text
    
    try:
        # Create service instance for URL generation
        # This handles both local (static files) and AWS (S3 pre-signed URLs)
        service = EducationService(db)
        
        # Query the education_pdfs table directly
        result = db.execute(
            text("""
                SELECT id, symptom_code, symptom_name, title, source, 
                       file_path, summary, keywords, display_order
                FROM education_pdfs 
                WHERE is_active = true 
                ORDER BY symptom_name, display_order
                LIMIT :limit
            """),
            {"limit": limit}
        ).fetchall()
        
        pdfs = []
        for row in result:
            file_path = row[5]
            # Generate proper URL based on environment (local or AWS S3)
            try:
                pdf_url = service._generate_presigned_url(file_path)
            except Exception as url_error:
                logger.warning(f"Failed to generate URL for {file_path}: {url_error}")
                # Fallback to local static path
                pdf_url = f"/static/education/{file_path}"
            
            pdfs.append({
                "id": str(row[0]),
                "symptom_code": row[1],
                "symptom_name": row[2],
                "title": row[3],
                "source": row[4],
                "file_path": file_path,
                "pdf_url": pdf_url,
                "summary": row[6],
                "keywords": row[7] or [],
            })
        
        # Also get handbooks
        handbooks_result = db.execute(
            text("""
                SELECT id, title, description, file_path, handbook_type
                FROM education_handbooks
                WHERE is_active = true
                ORDER BY display_order
            """)
        ).fetchall()
        
        handbooks = []
        for row in handbooks_result:
            file_path = row[3]
            # Generate proper URL based on environment (local or AWS S3)
            try:
                pdf_url = service._generate_presigned_url(file_path)
            except Exception as url_error:
                logger.warning(f"Failed to generate URL for handbook {file_path}: {url_error}")
                # Fallback to local static path
                pdf_url = f"/static/education/{file_path}"
            
            handbooks.append({
                "id": str(row[0]),
                "title": row[1],
                "description": row[2],
                "file_path": file_path,
                "pdf_url": pdf_url,
                "handbook_type": row[4],
            })
        
        return {
            "symptom_pdfs": pdfs,
            "handbooks": handbooks,
            "total_pdfs": len(pdfs),
            "total_handbooks": len(handbooks),
        }
    except Exception as e:
        logger.error(f"Error fetching education PDFs: {e}")
        # Return empty response if tables don't exist
        return {
            "symptom_pdfs": [],
            "handbooks": [],
            "total_pdfs": 0,
            "total_handbooks": 0,
        }


@router.get(
    "/search",
    response_model=List[EducationDocument],
    summary="Search education documents",
    description="Simple SQL ILIKE search. No embeddings, no NLP.",
)
async def search_education(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Search education documents."""
    service = EducationService(db)
    
    results = service.search_education(query=q, limit=limit)
    
    return results


@router.get(
    "/document/{document_id}",
    response_model=EducationDocument,
    summary="Get specific education document",
)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Get a specific education document with pre-signed URL."""
    from db.models.education import EducationDocument as EduDoc
    
    doc = db.query(EduDoc).filter(
        EduDoc.id == document_id,
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    
    # Log access
    service = EducationService(db)
    service.log_education_access(
        patient_id=patient_uuid,
        document_id=document_id,
        access_type="view",
        source="education_tab",
    )
    
    # Format response
    return service._format_education_doc(doc)


# =============================================================================
# SYMPTOMS CATALOG (Read-Only)
# =============================================================================

@router.get(
    "/symptoms",
    summary="Get symptom catalog",
    description="Get list of all active symptoms for reference.",
)
async def get_symptoms(
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Get symptom catalog."""
    from db.models.education import Symptom
    
    symptoms = db.query(Symptom).filter(
        Symptom.active == True
    ).order_by(Symptom.display_order).all()
    
    return [
        {
            "code": s.code,
            "name": s.name,
            "category": s.category,
            "description": s.description,
        }
        for s in symptoms
    ]


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@router.post(
    "/session",
    summary="Create symptom session",
    description="Create a new symptom session for tracking.",
)
async def create_session(
    conversation_uuid: Optional[UUID] = None,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Create a new symptom session."""
    service = EducationService(db)
    
    session = service.create_symptom_session(
        patient_id=patient_uuid,
        conversation_uuid=conversation_uuid,
    )
    
    return {
        "session_id": str(session.id),
        "status": session.status,
        "created_at": session.created_at.isoformat(),
    }


@router.get(
    "/session/{session_id}",
    summary="Get session details",
)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_patient_db),
    patient_uuid: UUID = Depends(get_current_patient_uuid),
):
    """Get symptom session details."""
    from db.models.education import SymptomSession
    
    session = db.query(SymptomSession).filter(
        SymptomSession.id == session_id,
        SymptomSession.patient_id == patient_uuid,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    return {
        "session_id": str(session.id),
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "selected_symptoms": session.selected_symptoms,
        "highest_severity": session.highest_severity,
        "escalation_triggered": session.escalation_triggered,
        "education_delivered": session.education_delivered,
        "summary_generated": session.summary_generated,
    }


# =============================================================================
# DISCLAIMER (Admin Reference)
# =============================================================================

@router.get(
    "/disclaimer",
    response_model=DisclaimerResponse,
    summary="Get mandatory disclaimer",
    description="Get the active mandatory disclaimer text.",
)
async def get_disclaimer(
    db: Session = Depends(get_patient_db),
):
    """Get mandatory disclaimer."""
    service = EducationService(db)
    return service._get_mandatory_disclaimer()



