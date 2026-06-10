"""
Summary Service - Patient API
==============================

Service for conversation summary operations.

Usage:
    from services import SummaryService
    
    summary_service = SummaryService(db)
    summaries = summary_service.get_by_month(patient_uuid, 2024, 1)
"""

from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from db.repositories import SummaryRepository
from core.logging import get_logger
from core.exceptions import NotFoundError, ValidationError
from utils.timezone_utils import utc_to_user_timezone

logger = get_logger(__name__)


class SummaryService:
    """
    Service for conversation summary operations.
    
    Provides:
    - Get summaries by month
    - Get summary details
    - Get recent summaries
    """
    
    def __init__(self, db: Session):
        """
        Initialize the summary service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.summary_repo = SummaryRepository(db)
    
    def _convert_to_dict(
        self,
        conversation: Any,
        timezone: str,
    ) -> Dict[str, Any]:
        """Convert conversation to dict with timezone-adjusted timestamps."""
        return {
            "uuid": str(conversation.uuid),
            "created_at": utc_to_user_timezone(conversation.created_at, timezone) if conversation.created_at else None,
            "updated_at": utc_to_user_timezone(conversation.updated_at, timezone) if conversation.updated_at else None,
            "conversation_state": conversation.conversation_state,
            "symptom_list": conversation.symptom_list,
            "severity_list": conversation.severity_list,
            "longer_summary": conversation.longer_summary,
            "medication_list": conversation.medication_list,
            "bulleted_summary": conversation.bulleted_summary,
            "overall_feeling": conversation.overall_feeling,
        }
    
    def get_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
        timezone: str = "America/Los_Angeles",
    ) -> List[Dict[str, Any]]:
        """
        Get conversation summaries for a specific month.
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            timezone: User's timezone
            
        Returns:
            List of conversation summaries
        """
        if month < 1 or month > 12:
            raise ValidationError(
                message="Month must be between 1 and 12",
                field="month",
            )
        
        logger.info(f"Get summaries by month: patient={patient_uuid} {year}/{month}")
        
        conversations = self.summary_repo.get_by_month(patient_uuid, year, month)
        
        logger.info(f"Found {len(conversations)} summaries")
        
        return [self._convert_to_dict(c, timezone) for c in conversations]
    
    def get_by_uuid(
        self,
        conversation_uuid: UUID,
        patient_uuid: UUID,
        timezone: str = "America/Los_Angeles",
    ) -> Dict[str, Any]:
        """
        Get a specific conversation summary.
        
        Args:
            conversation_uuid: The conversation's UUID
            patient_uuid: The patient's UUID
            timezone: User's timezone
            
        Returns:
            The conversation summary
            
        Raises:
            NotFoundError: If conversation not found
        """
        logger.info(f"Get summary: conversation={conversation_uuid}")
        
        conversation = self.summary_repo.get_by_uuid(conversation_uuid, patient_uuid)
        
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                resource_type="Conversation",
                resource_id=str(conversation_uuid),
            )
        
        return self._convert_to_dict(conversation, timezone)
    
    def get_recent(
        self,
        patient_uuid: UUID,
        limit: int = 10,
        timezone: str = "America/Los_Angeles",
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation summaries.
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            timezone: User's timezone
            
        Returns:
            List of recent conversation summaries
        """
        logger.info(f"Get recent summaries: patient={patient_uuid} limit={limit}")
        
        conversations = self.summary_repo.get_recent(patient_uuid, limit)
        
        return [self._convert_to_dict(c, timezone) for c in conversations]
    
    def count_conversations(
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
        return self.summary_repo.count_by_patient(patient_uuid)





