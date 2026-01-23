"""
Audit Logging Service

HIPAA-compliant audit trail for PHI access.
Logs all access attempts, modifications, and exports.
"""

from datetime import datetime, timedelta
from typing import Any, Callable
from collections import deque
import structlog

from aegis_auth.models import AuditEntry, User, AccessPurpose
from aegis_auth.tenancy import get_current_tenant, get_current_user

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Audit logging service for HIPAA compliance.
    
    Features:
    - Structured audit entries
    - Multiple output destinations (file, DB, SIEM)
    - Queryable audit trail
    - Retention management
    """
    
    def __init__(self, storage: Any = None):
        self._storage = storage or InMemoryAuditStorage()
        self._handlers: list[Callable[[AuditEntry], None]] = []
    
    def add_handler(self, handler: Callable[[AuditEntry], None]) -> None:
        """Add an audit event handler (e.g., send to Splunk)."""
        self._handlers.append(handler)
    
    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry."""
        # Store
        await self._storage.save(entry)
        
        # Call handlers
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception as e:
                logger.error("Audit handler failed", error=str(e))
        
        # Also log via structlog for immediate visibility
        log_method = logger.info if entry.success else logger.warning
        log_method(
            f"AUDIT: {entry.event_type}",
            user=entry.user_email,
            resource=entry.resource_type,
            success=entry.success,
        )
    
    async def log_access(
        self,
        resource_type: str,
        resource_id: str | None = None,
        patient_id: str | None = None,
        purpose: AccessPurpose = AccessPurpose.TREATMENT,
        success: bool = True,
        user: User | None = None,
        **kwargs
    ) -> AuditEntry:
        """Convenience method to log resource access."""
        user = user or get_current_user()
        tenant = get_current_tenant()
        
        entry = AuditEntry(
            event_type="access",
            user_id=user.id if user else "unknown",
            user_email=user.email if user else None,
            tenant_id=tenant.id if tenant else "unknown",
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            purpose=purpose,
            success=success,
            **kwargs
        )
        
        await self.log(entry)
        return entry
    
    async def log_modification(
        self,
        resource_type: str,
        resource_id: str,
        action: str,  # create, update, delete
        changes: dict | None = None,
        user: User | None = None,
    ) -> AuditEntry:
        """Log data modification."""
        user = user or get_current_user()
        tenant = get_current_tenant()
        
        entry = AuditEntry(
            event_type="modify",
            user_id=user.id if user else "unknown",
            user_email=user.email if user else None,
            tenant_id=tenant.id if tenant else "unknown",
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={"action": action, "changes": changes},
        )
        
        await self.log(entry)
        return entry
    
    async def log_export(
        self,
        resource_type: str,
        record_count: int,
        format: str,
        destination: str,
        user: User | None = None,
    ) -> AuditEntry:
        """Log data export (HIPAA disclosure tracking)."""
        user = user or get_current_user()
        tenant = get_current_tenant()
        
        entry = AuditEntry(
            event_type="export",
            user_id=user.id if user else "unknown",
            user_email=user.email if user else None,
            tenant_id=tenant.id if tenant else "unknown",
            resource_type=resource_type,
            metadata={
                "record_count": record_count,
                "format": format,
                "destination": destination,
            },
        )
        
        await self.log(entry)
        return entry
    
    async def log_break_glass(
        self,
        patient_id: str,
        reason: str,
        user: User | None = None,
    ) -> AuditEntry:
        """Log emergency/break-glass access."""
        user = user or get_current_user()
        tenant = get_current_tenant()
        
        entry = AuditEntry(
            event_type="break_glass",
            user_id=user.id if user else "unknown",
            user_email=user.email if user else None,
            tenant_id=tenant.id if tenant else "unknown",
            resource_type="Patient",
            patient_id=patient_id,
            purpose=AccessPurpose.EMERGENCY,
            purpose_detail=reason,
        )
        
        await self.log(entry)
        
        # Break-glass should alert security team
        logger.critical(
            "BREAK-GLASS ACCESS",
            user=user.email if user else "unknown",
            patient=patient_id,
            reason=reason,
        )
        
        return entry
    
    async def query(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        patient_id: str | None = None,
        resource_type: str | None = None,
        event_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit trail."""
        return await self._storage.query(
            tenant_id=tenant_id,
            user_id=user_id,
            patient_id=patient_id,
            resource_type=resource_type,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    
    async def get_patient_access_history(
        self,
        patient_id: str,
        days: int = 90,
    ) -> list[AuditEntry]:
        """Get all access to a patient's records (for patient request)."""
        start = datetime.utcnow() - timedelta(days=days)
        return await self.query(
            patient_id=patient_id,
            start_date=start,
        )


class InMemoryAuditStorage:
    """In-memory audit storage for development."""
    
    def __init__(self, max_entries: int = 10000):
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)
    
    async def save(self, entry: AuditEntry) -> None:
        self._entries.append(entry)
    
    async def query(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        patient_id: str | None = None,
        resource_type: str | None = None,
        event_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = []
        
        for entry in reversed(self._entries):
            if len(results) >= limit:
                break
            
            if tenant_id and entry.tenant_id != tenant_id:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if patient_id and entry.patient_id != patient_id:
                continue
            if resource_type and entry.resource_type != resource_type:
                continue
            if event_type and entry.event_type != event_type:
                continue
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            
            results.append(entry)
        
        return results


# Global audit service instance
_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """Get the global audit service."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


async def audit_access(
    resource_type: str,
    resource_id: str | None = None,
    **kwargs
) -> AuditEntry:
    """Convenience function to log access."""
    return await get_audit_service().log_access(
        resource_type=resource_type,
        resource_id=resource_id,
        **kwargs
    )
