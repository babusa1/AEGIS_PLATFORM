"""
HIPAA Audit Logging

Comprehensive audit trail for:
- Data access
- PHI operations
- User actions
- System events
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import uuid

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Audit Event Types
# =============================================================================

class AuditEventType(str, Enum):
    """Types of audit events."""
    # Data access
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # PHI operations
    PHI_ACCESS = "phi.access"
    PHI_DISCLOSURE = "phi.disclosure"
    PHI_AMENDMENT = "phi.amendment"
    
    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_MFA = "auth.mfa"
    
    # Authorization
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    BTG_ACTIVATED = "btg.activated"  # Break-the-glass
    BTG_DEACTIVATED = "btg.deactivated"
    
    # User management
    USER_CREATED = "user.created"
    USER_MODIFIED = "user.modified"
    USER_DELETED = "user.deleted"
    ROLE_CHANGED = "role.changed"
    
    # System events
    CONFIG_CHANGED = "config.changed"
    SYSTEM_ERROR = "system.error"
    SECURITY_ALERT = "security.alert"
    
    # Workflow
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    AGENT_INVOKED = "agent.invoked"


class AuditSeverity(str, Enum):
    """Audit event severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Audit Event Model
# =============================================================================

class AuditEvent(BaseModel):
    """A single audit event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event type
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.LOW
    
    # Actor (who)
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Action (what)
    action: str
    resource_type: Optional[str] = None  # patient, claim, workflow, etc.
    resource_id: Optional[str] = None
    
    # Context (how/where)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Details
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None
    
    # PHI flag
    contains_phi: bool = False
    phi_types: List[str] = Field(default_factory=list)
    
    def to_log_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "audit_id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "success": self.success,
            "contains_phi": self.contains_phi,
        }


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """
    HIPAA-compliant audit logger.
    
    Features:
    - Structured audit events
    - PHI detection in audit data
    - Multiple output destinations
    - Immutable logging
    """
    
    def __init__(
        self,
        pool=None,  # Database connection pool
        kafka_producer=None,  # For streaming
        detect_phi: bool = True,
    ):
        self.pool = pool
        self.kafka_producer = kafka_producer
        self.detect_phi = detect_phi
        
        # PHI detector for audit data
        if detect_phi:
            from aegis.security.phi import PHIDetector
            self._phi_detector = PHIDetector(sensitivity="high")
        else:
            self._phi_detector = None
        
        # In-memory buffer for batch inserts
        self._buffer: List[AuditEvent] = []
        self._max_buffer = 100
    
    async def log(self, event: AuditEvent) -> str:
        """
        Log an audit event.
        
        Returns the event ID.
        """
        # Detect PHI in event details
        if self._phi_detector and event.details:
            details_str = json.dumps(event.details)
            if self._phi_detector.contains_phi(details_str):
                event.contains_phi = True
                event.phi_types = [
                    t.value for t in self._phi_detector.get_phi_types(details_str)
                ]
        
        # Log to structured logger
        logger.info(
            "audit_event",
            **event.to_log_dict(),
        )
        
        # Buffer for database
        self._buffer.append(event)
        
        # Flush if buffer is full
        if len(self._buffer) >= self._max_buffer:
            await self.flush()
        
        # Stream to Kafka if available
        if self.kafka_producer:
            await self._stream_event(event)
        
        return event.id
    
    async def _stream_event(self, event: AuditEvent):
        """Stream event to Kafka."""
        try:
            await self.kafka_producer.send_and_wait(
                topic="aegis.audit",
                value=event.json().encode(),
            )
        except Exception as e:
            logger.error(f"Failed to stream audit event: {e}")
    
    async def flush(self):
        """Flush buffer to database."""
        if not self._buffer or not self.pool:
            return
        
        events_to_flush = self._buffer.copy()
        self._buffer.clear()
        
        try:
            async with self.pool.acquire() as conn:
                for event in events_to_flush:
                    await conn.execute("""
                        INSERT INTO audit_log (
                            id, timestamp, event_type, severity,
                            user_id, tenant_id, action,
                            resource_type, resource_id,
                            ip_address, session_id,
                            details, success, error_message,
                            contains_phi
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    """,
                        event.id,
                        event.timestamp,
                        event.event_type.value,
                        event.severity.value,
                        event.user_id,
                        event.tenant_id,
                        event.action,
                        event.resource_type,
                        event.resource_id,
                        event.ip_address,
                        event.session_id,
                        json.dumps(event.details),
                        event.success,
                        event.error_message,
                        event.contains_phi,
                    )
            
            logger.debug(f"Flushed {len(events_to_flush)} audit events to database")
            
        except Exception as e:
            logger.error(f"Failed to flush audit events: {e}")
            # Re-add to buffer
            self._buffer.extend(events_to_flush)
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str = "read",
        details: dict = None,
        **kwargs,
    ) -> str:
        """Log data access event."""
        event = AuditEvent(
            event_type=AuditEventType.DATA_READ if action == "read" else AuditEventType.DATA_WRITE,
            user_id=user_id,
            action=f"data.{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            **kwargs,
        )
        return await self.log(event)
    
    async def log_phi_access(
        self,
        user_id: str,
        patient_id: str,
        reason: str,
        phi_types: List[str] = None,
        **kwargs,
    ) -> str:
        """Log PHI access event."""
        event = AuditEvent(
            event_type=AuditEventType.PHI_ACCESS,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            action="phi.access",
            resource_type="patient",
            resource_id=patient_id,
            details={"reason": reason},
            contains_phi=True,
            phi_types=phi_types or [],
            **kwargs,
        )
        return await self.log(event)
    
    async def log_auth_event(
        self,
        event_type: AuditEventType,
        user_id: str = None,
        success: bool = True,
        details: dict = None,
        **kwargs,
    ) -> str:
        """Log authentication event."""
        severity = AuditSeverity.LOW if success else AuditSeverity.HIGH
        
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            action=event_type.value,
            success=success,
            details=details or {},
            **kwargs,
        )
        return await self.log(event)
    
    async def log_btg(
        self,
        user_id: str,
        patient_id: str,
        reason: str,
        activated: bool = True,
        **kwargs,
    ) -> str:
        """Log break-the-glass event."""
        event = AuditEvent(
            event_type=AuditEventType.BTG_ACTIVATED if activated else AuditEventType.BTG_DEACTIVATED,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            action="btg.activate" if activated else "btg.deactivate",
            resource_type="patient",
            resource_id=patient_id,
            details={"reason": reason},
            contains_phi=True,
            **kwargs,
        )
        return await self.log(event)
    
    async def log_security_alert(
        self,
        alert_type: str,
        description: str,
        details: dict = None,
        **kwargs,
    ) -> str:
        """Log security alert."""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_ALERT,
            severity=AuditSeverity.CRITICAL,
            action=f"security.{alert_type}",
            details={
                "description": description,
                **(details or {}),
            },
            **kwargs,
        )
        return await self.log(event)
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    async def get_events(
        self,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        event_type: AuditEventType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events from database."""
        if not self.pool:
            return []
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        param_idx = 1
        
        if user_id:
            query += f" AND user_id = ${param_idx}"
            params.append(user_id)
            param_idx += 1
        
        if resource_type:
            query += f" AND resource_type = ${param_idx}"
            params.append(resource_type)
            param_idx += 1
        
        if resource_id:
            query += f" AND resource_id = ${param_idx}"
            params.append(resource_id)
            param_idx += 1
        
        if event_type:
            query += f" AND event_type = ${param_idx}"
            params.append(event_type.value)
            param_idx += 1
        
        if start_time:
            query += f" AND timestamp >= ${param_idx}"
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            query += f" AND timestamp <= ${param_idx}"
            params.append(end_time)
            param_idx += 1
        
        query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
        params.append(limit)
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
            return [
                AuditEvent(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    event_type=AuditEventType(row["event_type"]),
                    severity=AuditSeverity(row["severity"]),
                    user_id=row["user_id"],
                    tenant_id=row["tenant_id"],
                    action=row["action"],
                    resource_type=row["resource_type"],
                    resource_id=row["resource_id"],
                    ip_address=row["ip_address"],
                    session_id=row["session_id"],
                    details=json.loads(row["details"]) if row["details"] else {},
                    success=row["success"],
                    error_message=row["error_message"],
                    contains_phi=row["contains_phi"],
                )
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []


# =============================================================================
# Global Instance
# =============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(pool=None, kafka_producer=None) -> AuditLogger:
    """Configure global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(pool=pool, kafka_producer=kafka_producer)
    return _audit_logger
