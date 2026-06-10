"""
Summary Repository - Patient API
================================

Repository for conversation summary operations.

Usage:
    from db.repositories import SummaryRepository
    
    summary_repo = SummaryRepository(db)
    summaries = summary_repo.get_by_month(patient_uuid, 2024, 1)
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import extract

from .base import BaseRepository
# Use legacy model - matches actual database table
from db.patient_models import Conversations as Conversation
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)


class SummaryRepository(BaseRepository[Conversation]):
    """
    Repository for Conversation summary operations.
    
    Provides read operations for retrieving completed
    conversation summaries.
    """
    
    def __init__(self, db: Session):
        """Initialize the summary repository."""
        super().__init__(Conversation, db)
    
    def get_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
    ) -> List[Conversation]:
        """
        Get conversation summaries for a specific month.
        
        Only returns conversations that have been processed
        (have a bulleted_summary).
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            
        Returns:
            List of Conversation instances with summaries
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid,
            Conversation.bulleted_summary.isnot(None),
            extract('year', Conversation.created_at) == year,
            extract('month', Conversation.created_at) == month,
        ).order_by(Conversation.created_at.desc()).all()
    
    def get_by_uuid(
        self,
        conversation_uuid: UUID,
        patient_uuid: UUID,
    ) -> Optional[Conversation]:
        """
        Get a specific conversation by UUID.
        
        Only returns if it has been processed (has a bulleted_summary).
        
        Args:
            conversation_uuid: The conversation's UUID
            patient_uuid: The patient's UUID (for authorization)
            
        Returns:
            The Conversation instance, or None if not found
        """
        return self.db.query(Conversation).filter(
            Conversation.uuid == conversation_uuid,
            Conversation.patient_uuid == patient_uuid,
            Conversation.bulleted_summary.isnot(None),
        ).first()
    
    def get_by_uuid_or_fail(
        self,
        conversation_uuid: UUID,
        patient_uuid: UUID,
    ) -> Conversation:
        """
        Get a specific conversation by UUID, raising error if not found.
        
        Args:
            conversation_uuid: The conversation's UUID
            patient_uuid: The patient's UUID
            
        Returns:
            The Conversation instance
            
        Raises:
            NotFoundError: If conversation not found
        """
        conversation = self.get_by_uuid(conversation_uuid, patient_uuid)
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                resource_type="Conversation",
                resource_id=str(conversation_uuid),
            )
        return conversation
    
    def get_recent(
        self,
        patient_uuid: UUID,
        limit: int = 10,
    ) -> List[Conversation]:
        """
        Get recent conversation summaries.
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            
        Returns:
            List of recent Conversation instances with summaries
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid,
            Conversation.bulleted_summary.isnot(None),
        ).order_by(Conversation.created_at.desc()).limit(limit).all()
    
    def get_with_alerts(
        self,
        patient_uuid: UUID,
        limit: int = 50,
    ) -> List[Conversation]:
        """
        Get conversations that triggered alerts based on triage level.
        
        Alert-worthy triage levels:
        - call_911: Emergency situation requiring immediate action
        - notify_care_team: Needs care team attention
        - urgent: Requires prompt follow-up
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            
        Returns:
            List of Conversation instances with alert-level triage
        """
        alert_triage_levels = ['call_911', 'notify_care_team', 'urgent']
        
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid,
            Conversation.triage_level.in_(alert_triage_levels),
        ).order_by(Conversation.created_at.desc()).limit(limit).all()
    
    def count_by_patient(
        self,
        patient_uuid: UUID,
    ) -> int:
        """
        Count completed conversations for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            Number of completed conversations
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid,
            Conversation.bulleted_summary.isnot(None),
        ).count()

