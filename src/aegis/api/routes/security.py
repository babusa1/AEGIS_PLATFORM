"""
Security API Routes

Endpoints for:
- PHI Detection
- PHI Redaction
- Audit Log
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aegis.security.phi import (
    PHIDetector, PHIRedactor, PHIType, RedactionStrategy,
    detect_phi, redact_phi, contains_phi,
)
from aegis.security.audit import (
    AuditLogger, AuditEvent, AuditEventType, get_audit_logger,
)

router = APIRouter(prefix="/security", tags=["security"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PHIDetectRequest(BaseModel):
    text: str
    sensitivity: str = "high"  # low, medium, high


class PHIRedactRequest(BaseModel):
    text: str
    strategy: str = "mask"  # mask, hash, category, remove, partial
    sensitivity: str = "high"


class AuditLogRequest(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: dict = None
    success: bool = True


# =============================================================================
# PHI Detection Endpoints
# =============================================================================

@router.post("/phi/detect")
async def detect_phi_endpoint(request: PHIDetectRequest):
    """
    Detect PHI (Protected Health Information) in text.
    
    Identifies HIPAA 18 identifiers including:
    - Names, SSN, MRN
    - Dates, addresses, phone numbers
    - Email, IP addresses
    """
    detector = PHIDetector(sensitivity=request.sensitivity)
    matches = detector.detect(request.text)
    
    return {
        "contains_phi": len(matches) > 0,
        "match_count": len(matches),
        "phi_types": list({m.phi_type.value for m in matches}),
        "matches": [
            {
                "type": m.phi_type.value,
                "text": m.text,
                "start": m.start,
                "end": m.end,
                "confidence": m.confidence,
            }
            for m in matches
        ],
    }


@router.post("/phi/redact")
async def redact_phi_endpoint(request: PHIRedactRequest):
    """
    Redact PHI from text.
    
    Strategies:
    - mask: Replace with [REDACTED]
    - hash: Replace with hash
    - category: Replace with [PHI_TYPE]
    - remove: Remove entirely
    - partial: Partial mask (e.g., ***-**-1234)
    """
    detector = PHIDetector(sensitivity=request.sensitivity)
    
    strategy = RedactionStrategy(request.strategy)
    redactor = PHIRedactor(
        detector=detector,
        default_strategy=strategy,
    )
    
    redacted_text, matches = redactor.redact(request.text, return_matches=True)
    
    return {
        "original_length": len(request.text),
        "redacted_length": len(redacted_text),
        "redacted_text": redacted_text,
        "redactions_applied": len(matches),
        "phi_types_redacted": list({m.phi_type.value for m in matches}),
    }


@router.post("/phi/check")
async def check_phi_endpoint(text: str = Query(...)):
    """Quick check if text contains PHI."""
    has_phi = contains_phi(text)
    return {"contains_phi": has_phi}


@router.get("/phi/types")
async def list_phi_types():
    """List all supported PHI types (HIPAA 18)."""
    return {
        "phi_types": [
            {"value": t.value, "name": t.name}
            for t in PHIType
        ],
        "description": "HIPAA 18 Protected Health Information identifiers",
    }


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.post("/audit/log")
async def create_audit_log(request: AuditLogRequest):
    """Create an audit log entry."""
    audit_logger = get_audit_logger()
    
    try:
        event_type = AuditEventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}"
        )
    
    event = AuditEvent(
        event_type=event_type,
        user_id=request.user_id,
        action=request.action,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        details=request.details or {},
        success=request.success,
    )
    
    event_id = await audit_logger.log(event)
    
    return {"event_id": event_id, "status": "logged"}


@router.get("/audit/events")
async def get_audit_events(
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
):
    """Query audit log events."""
    audit_logger = get_audit_logger()
    
    et = None
    if event_type:
        try:
            et = AuditEventType(event_type)
        except ValueError:
            pass
    
    events = await audit_logger.get_events(
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=et,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    return {
        "total": len(events),
        "events": [e.dict() for e in events],
    }


@router.get("/audit/event-types")
async def list_event_types():
    """List all audit event types."""
    return {
        "event_types": [
            {"value": t.value, "name": t.name}
            for t in AuditEventType
        ],
    }


# =============================================================================
# Compliance Endpoints
# =============================================================================

@router.get("/compliance/summary")
async def get_compliance_summary():
    """Get HIPAA compliance summary."""
    audit_logger = get_audit_logger()
    
    # Get recent events
    events = await audit_logger.get_events(limit=1000)
    
    # Analyze
    phi_access_count = len([e for e in events if e.event_type == AuditEventType.PHI_ACCESS])
    btg_count = len([e for e in events if e.event_type == AuditEventType.BTG_ACTIVATED])
    security_alerts = len([e for e in events if e.event_type == AuditEventType.SECURITY_ALERT])
    failed_auth = len([e for e in events if e.event_type == AuditEventType.AUTH_FAILED])
    
    return {
        "summary": {
            "total_events": len(events),
            "phi_access_events": phi_access_count,
            "break_the_glass_events": btg_count,
            "security_alerts": security_alerts,
            "failed_authentications": failed_auth,
        },
        "status": "compliant" if security_alerts == 0 else "review_needed",
        "recommendations": [
            "Review all BTG events" if btg_count > 0 else None,
            "Investigate failed auth attempts" if failed_auth > 5 else None,
        ],
    }
