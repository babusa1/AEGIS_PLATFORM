"""
Audit Log API Routes

Endpoints for querying and verifying immutable audit logs.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import structlog

from aegis.api.auth import get_current_user, User
from aegis.security.audit import AuditEventType, AuditSeverity
from aegis.security.immutable_audit import get_immutable_audit_logger

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditEventResponse(BaseModel):
    """Audit event response model."""
    id: str
    timestamp: datetime
    event_type: str
    severity: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    success: bool
    contains_phi: bool


class IntegrityVerificationResponse(BaseModel):
    """Integrity verification response."""
    verified: bool
    total_records: int
    tampered_records: List[dict]
    last_chain_hash: Optional[str]
    error: Optional[str] = None


@router.get("/events", response_model=List[AuditEventResponse])
async def get_audit_events(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
):
    """
    Query immutable audit events.
    
    Requires appropriate permissions. Returns read-only audit records.
    """
    # Check permissions (only admins/auditors can query audit logs)
    user_roles = current_user.roles if hasattr(current_user, 'roles') else []
    if "admin" not in user_roles and "auditor" not in user_roles:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to access audit logs"
        )
    
    try:
        # Get database pool from app state
        from aegis.db import get_db_clients
        db_clients = await get_db_clients()
        pool = db_clients.postgres if db_clients else None
        
        if not pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        immutable_logger = get_immutable_audit_logger(pool=pool)
        
        # Parse event type if provided
        parsed_event_type = None
        if event_type:
            try:
                parsed_event_type = AuditEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {event_type}"
                )
        
        events = await immutable_logger.get_events(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=parsed_event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        
        return [
            AuditEventResponse(
                id=str(event.id),
                timestamp=event.timestamp,
                event_type=event.event_type.value,
                severity=event.severity.value,
                user_id=event.user_id,
                tenant_id=event.tenant_id,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                success=event.success,
                contains_phi=event.contains_phi,
            )
            for event in events
        ]
        
    except Exception as e:
        logger.error("Failed to query audit events", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to query audit events: {str(e)}")


@router.get("/verify-integrity", response_model=IntegrityVerificationResponse)
async def verify_audit_integrity(
    start_sequence: Optional[int] = Query(None, description="Start sequence number"),
    end_sequence: Optional[int] = Query(None, description="End sequence number"),
    current_user: User = Depends(get_current_user),
):
    """
    Verify integrity of immutable audit log hash chain.
    
    Checks for tampering by validating hash chain. Only admins can verify.
    """
    # Check permissions
    user_roles = current_user.roles if hasattr(current_user, 'roles') else []
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can verify audit log integrity"
        )
    
    try:
        from aegis.db import get_db_clients
        
        # Get database clients (sync function that returns global instance)
        db_clients = get_db_clients()
        pool = db_clients.postgres if db_clients else None
        
        if not pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        immutable_logger = get_immutable_audit_logger(pool=pool)
        
        result = await immutable_logger.verify_integrity(
            start_sequence=start_sequence,
            end_sequence=end_sequence,
        )
        
        return IntegrityVerificationResponse(**result)
        
    except Exception as e:
        logger.error("Failed to verify audit integrity", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify integrity: {str(e)}"
        )
