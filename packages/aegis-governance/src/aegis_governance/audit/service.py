"""Audit Trail Service - HITRUST 09.aa"""
from dataclasses import asdict
from datetime import datetime
from typing import Any
import hashlib
import json
import uuid
import structlog

from aegis_governance.audit.models import AuditEvent, AuditQuery, AuditCategory, AuditSeverity

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Immutable audit trail service.
    
    HITRUST 09.aa: Audit logging
    SOC 2 Security: Security event logging
    """
    
    def __init__(self, storage_backend=None):
        self._events: list[AuditEvent] = []
        self._storage = storage_backend
        self._last_hash: str | None = None
    
    def log(self, category: AuditCategory, action: str, actor_id: str,
           actor_type: str, resource_type: str, resource_id: str,
           tenant_id: str, outcome: str = "success",
           severity: AuditSeverity = AuditSeverity.INFO,
           patient_id: str | None = None, ip_address: str | None = None,
           details: dict | None = None) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            id=f"AUD-{uuid.uuid4().hex[:16].upper()}",
            timestamp=datetime.utcnow(),
            category=category,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            outcome=outcome,
            severity=severity,
            patient_id=patient_id,
            ip_address=ip_address,
            details=details or {}
        )
        
        # Chain hash for integrity
        event.hash = self._compute_hash(event)
        self._last_hash = event.hash
        
        # Store
        self._events.append(event)
        if self._storage:
            self._storage.store(event)
        
        # Log high severity events
        if severity in (AuditSeverity.ALERT, AuditSeverity.CRITICAL):
            logger.warning("Audit alert", event_id=event.id, action=action,
                          category=category.value, severity=severity.value)
        
        return event
    
    def log_access(self, actor_id: str, resource_type: str, resource_id: str,
                  tenant_id: str, action: str = "read", patient_id: str | None = None,
                  outcome: str = "success", ip_address: str | None = None) -> AuditEvent:
        """Convenience method for access logging."""
        return self.log(
            category=AuditCategory.ACCESS,
            action=action,
            actor_id=actor_id,
            actor_type="user",
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            patient_id=patient_id,
            outcome=outcome,
            ip_address=ip_address
        )
    
    def log_authentication(self, actor_id: str, tenant_id: str,
                          outcome: str, method: str = "password",
                          ip_address: str | None = None) -> AuditEvent:
        """Log authentication event."""
        severity = AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING
        return self.log(
            category=AuditCategory.AUTHENTICATION,
            action=f"login:{method}",
            actor_id=actor_id,
            actor_type="user",
            resource_type="session",
            resource_id="",
            tenant_id=tenant_id,
            outcome=outcome,
            severity=severity,
            ip_address=ip_address,
            details={"method": method}
        )
    
    def log_data_change(self, actor_id: str, resource_type: str, resource_id: str,
                       tenant_id: str, change_type: str, patient_id: str | None = None,
                       before: dict | None = None, after: dict | None = None) -> AuditEvent:
        """Log data modification."""
        return self.log(
            category=AuditCategory.DATA_CHANGE,
            action=change_type,
            actor_id=actor_id,
            actor_type="user",
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            patient_id=patient_id,
            details={"before": before, "after": after}
        )
    
    def log_btg(self, actor_id: str, patient_id: str, tenant_id: str,
               session_id: str, action: str) -> AuditEvent:
        """Log Break-the-Glass event."""
        return self.log(
            category=AuditCategory.BTG,
            action=action,
            actor_id=actor_id,
            actor_type="user",
            resource_type="btg_session",
            resource_id=session_id,
            tenant_id=tenant_id,
            patient_id=patient_id,
            severity=AuditSeverity.ALERT,
            details={"btg_session": session_id}
        )
    
    def query(self, query: AuditQuery) -> list[AuditEvent]:
        """Query audit events."""
        results = self._events
        
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.category:
            results = [e for e in results if e.category == query.category]
        if query.actor_id:
            results = [e for e in results if e.actor_id == query.actor_id]
        if query.patient_id:
            results = [e for e in results if e.patient_id == query.patient_id]
        if query.resource_type:
            results = [e for e in results if e.resource_type == query.resource_type]
        if query.outcome:
            results = [e for e in results if e.outcome == query.outcome]
        if query.tenant_id:
            results = [e for e in results if e.tenant_id == query.tenant_id]
        
        # Sort by timestamp descending
        results = sorted(results, key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        return results[query.offset:query.offset + query.limit]
    
    def verify_integrity(self) -> bool:
        """Verify audit trail integrity using hash chain."""
        prev_hash = None
        for event in self._events:
            expected = self._compute_hash(event, prev_hash)
            if event.hash != expected:
                logger.error("Audit integrity violation", event_id=event.id)
                return False
            prev_hash = event.hash
        return True
    
    def _compute_hash(self, event: AuditEvent, prev_hash: str | None = None) -> str:
        """Compute hash for event integrity."""
        data = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "category": event.category.value,
            "action": event.action,
            "actor_id": event.actor_id,
            "resource_id": event.resource_id,
            "prev_hash": prev_hash or self._last_hash
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:32]
    
    def export(self, query: AuditQuery, format: str = "json") -> str:
        """Export audit events for compliance reporting."""
        events = self.query(query)
        if format == "json":
            return json.dumps([asdict(e) for e in events], default=str, indent=2)
        return ""
