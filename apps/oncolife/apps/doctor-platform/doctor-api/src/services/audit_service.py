"""
Audit Service - Doctor API
==========================

Service for HIPAA-compliant audit logging.

Tracks all access to patient data including:
- Dashboard views
- Patient record access
- Report downloads
- Data exports

All logs are immutable and timestamped for compliance.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from .base import BaseService
from core.logging import get_logger

logger = get_logger(__name__)


class AuditService(BaseService):
    """
    Service for HIPAA-compliant audit logging.
    
    Logs are:
    - Immutable (no updates/deletes)
    - Timestamped with UTC time
    - Include user, action, and entity details
    - Optional IP address and user agent
    """
    
    def __init__(self, db: Session):
        """
        Initialize the audit service.
        
        Args:
            db: Database session
        """
        super().__init__(db)
    
    def log_action(
        self,
        user_id: UUID,
        user_role: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an action for audit purposes.
        
        Args:
            user_id: UUID of the user performing the action
            user_role: Role of the user (physician, staff, admin)
            action: Action being performed (view_patient, download_report, etc.)
            entity_type: Type of entity being accessed (patient, conversation, etc.)
            entity_id: ID of the specific entity
            ip_address: IP address of the request
            user_agent: User agent string
            metadata: Additional context about the action
        """
        try:
            # Use raw SQL to insert into audit_logs table
            # This works even if the table doesn't exist yet (will fail gracefully)
            self.db.execute(
                text("""
                    INSERT INTO audit_logs (
                        id, user_id, user_role, action, entity_type, entity_id,
                        ip_address, user_agent, metadata, accessed_at
                    ) VALUES (
                        gen_random_uuid(), :user_id, :user_role, :action, 
                        :entity_type, :entity_id, :ip_address, :user_agent,
                        :metadata::jsonb, :accessed_at
                    )
                """),
                {
                    "user_id": str(user_id),
                    "user_role": user_role,
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id) if entity_id else None,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "metadata": str(metadata) if metadata else "{}",
                    "accessed_at": datetime.utcnow(),
                }
            )
            self.db.commit()
            
            logger.debug(
                f"Audit: user={user_id} action={action} "
                f"entity={entity_type}/{entity_id}"
            )
        except Exception as e:
            # Don't let audit logging failures break the application
            # Just log the error and continue
            logger.warning(f"Failed to log audit action: {e}")
            self.db.rollback()
    
    def log_patient_view(
        self,
        user_id: UUID,
        user_role: str,
        patient_id: UUID,
        view_type: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Log viewing patient data.
        
        Args:
            user_id: UUID of the user
            user_role: Role of the user
            patient_id: UUID of the patient being viewed
            view_type: Type of view (profile, timeline, diary, alerts)
            ip_address: IP address of the request
        """
        self.log_action(
            user_id=user_id,
            user_role=user_role,
            action=f"view_patient_{view_type}",
            entity_type="patient",
            entity_id=patient_id,
            ip_address=ip_address,
        )
    
    def log_report_access(
        self,
        user_id: UUID,
        user_role: str,
        report_id: UUID,
        action: str = "download",
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Log report access.
        
        Args:
            user_id: UUID of the user
            user_role: Role of the user
            report_id: UUID of the report
            action: Action (view, download, generate)
            ip_address: IP address of the request
        """
        self.log_action(
            user_id=user_id,
            user_role=user_role,
            action=f"report_{action}",
            entity_type="report",
            entity_id=report_id,
            ip_address=ip_address,
        )
    
    def log_login(
        self,
        user_id: UUID,
        user_role: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log login attempt.
        
        Args:
            user_id: UUID of the user
            user_role: Role of the user
            success: Whether login was successful
            ip_address: IP address of the request
            user_agent: User agent string
        """
        action = "login_success" if success else "login_failure"
        self.log_action(
            user_id=user_id,
            user_role=user_role,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
        )



