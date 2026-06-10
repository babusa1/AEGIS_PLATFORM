"""
Conversation Repository for Chat and Message Operations.

This repository handles all database operations related to
conversations and messages for the symptom checker.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, func

from db.models import Conversation, Message
from db.repositories.base import BaseRepository
from core.logging import get_logger

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    """
    Repository for Conversation and Message operations.
    
    Handles conversation lifecycle, message creation,
    and symptom tracking queries.
    """
    
    def __init__(self, db: Session):
        """Initialize with Conversation model."""
        super().__init__(Conversation, db)
    
    # =========================================================================
    # CONVERSATION QUERIES
    # =========================================================================
    
    def get_with_messages(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get conversation with all messages eagerly loaded.
        
        Args:
            conversation_id: Conversation UUID
        
        Returns:
            Conversation with messages or None
        """
        return self.db.query(Conversation).options(
            joinedload(Conversation.messages)
        ).filter(
            Conversation.uuid == conversation_id
        ).first()
    
    def get_patient_conversations(
        self,
        patient_uuid: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """
        Get all conversations for a patient.
        
        Args:
            patient_uuid: Patient UUID
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of conversations (newest first)
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid
        ).order_by(
            desc(Conversation.created_at)
        ).offset(skip).limit(limit).all()
    
    def get_latest_conversation(
        self,
        patient_uuid: UUID
    ) -> Optional[Conversation]:
        """
        Get the most recent conversation for a patient.
        
        Args:
            patient_uuid: Patient UUID
        
        Returns:
            Latest conversation or None
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid
        ).order_by(
            desc(Conversation.created_at)
        ).first()
    
    def get_active_conversation(
        self,
        patient_uuid: UUID
    ) -> Optional[Conversation]:
        """
        Get the active (incomplete) conversation for a patient.
        
        Args:
            patient_uuid: Patient UUID
        
        Returns:
            Active conversation or None
        """
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid,
            Conversation.is_complete != "true"
        ).order_by(
            desc(Conversation.created_at)
        ).first()
    
    def get_or_create_active_conversation(
        self,
        patient_uuid: UUID
    ) -> tuple[Conversation, bool]:
        """
        Get active conversation or create a new one.
        
        Args:
            patient_uuid: Patient UUID
        
        Returns:
            Tuple of (conversation, is_new)
        """
        # Check for existing active conversation
        existing = self.get_active_conversation(patient_uuid)
        if existing:
            return existing, False
        
        # Create new conversation
        new_conversation = self.create({
            "patient_uuid": patient_uuid,
            "conversation_state": "greeting",
            "symptom_list": [],
            "severity_list": [],
        })
        
        return new_conversation, True
    
    # =========================================================================
    # TRIAGE QUERIES
    # =========================================================================
    
    def get_emergency_conversations(
        self,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Get conversations that resulted in emergency triage.
        
        Args:
            since: Only get conversations after this time
            limit: Maximum results
        
        Returns:
            List of emergency conversations
        """
        query = self.db.query(Conversation).filter(
            Conversation.triage_level == "call_911"
        )
        
        if since:
            query = query.filter(Conversation.created_at >= since)
        
        return query.order_by(
            desc(Conversation.created_at)
        ).limit(limit).all()
    
    def get_care_team_alerts(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Get conversations that require care team notification.
        
        Args:
            since: Only get conversations after this time
            limit: Maximum results
        
        Returns:
            List of conversations needing review
        """
        query = self.db.query(Conversation).filter(
            Conversation.triage_level.in_(["call_911", "notify_care_team"])
        )
        
        if since:
            query = query.filter(Conversation.created_at >= since)
        
        return query.order_by(
            desc(Conversation.created_at)
        ).limit(limit).all()
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    def add_message(
        self,
        conversation_id: UUID,
        sender: str,
        content: str,
        message_type: str = "text",
        structured_data: Optional[dict] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation UUID
            sender: Message sender (user/assistant/system)
            content: Message text
            message_type: Type of message
            structured_data: Additional data (options, etc.)
        
        Returns:
            Created message
        """
        message = Message(
            chat_uuid=conversation_id,
            sender=sender,
            content=content,
            message_type=message_type,
            structured_data=structured_data
        )
        
        self.db.add(message)
        self.db.flush()
        
        logger.debug(
            f"Added message to conversation {conversation_id}",
            extra={"sender": sender, "type": message_type}
        )
        
        return message
    
    def get_messages(
        self,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation UUID
            skip: Offset for pagination
            limit: Maximum messages
        
        Returns:
            List of messages (oldest first)
        """
        return self.db.query(Message).filter(
            Message.chat_uuid == conversation_id
        ).order_by(
            Message.created_at
        ).offset(skip).limit(limit).all()
    
    def get_latest_messages(
        self,
        conversation_id: UUID,
        count: int = 10
    ) -> List[Message]:
        """
        Get the most recent messages in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            count: Number of messages to retrieve
        
        Returns:
            List of messages (newest first)
        """
        return self.db.query(Message).filter(
            Message.chat_uuid == conversation_id
        ).order_by(
            desc(Message.created_at)
        ).limit(count).all()
    
    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================
    
    def update_engine_state(
        self,
        conversation_id: UUID,
        engine_state: dict
    ) -> Conversation:
        """
        Update the symptom checker engine state.
        
        Args:
            conversation_id: Conversation UUID
            engine_state: Engine state dictionary
        
        Returns:
            Updated conversation
        """
        conversation = self.get_by_id_or_raise(conversation_id)
        conversation.engine_state = engine_state
        self.db.flush()
        return conversation
    
    def complete_conversation(
        self,
        conversation_id: UUID,
        triage_level: str,
        triage_message: str,
        summary: Optional[str] = None
    ) -> Conversation:
        """
        Mark a conversation as complete with triage result.
        
        Args:
            conversation_id: Conversation UUID
            triage_level: Final triage level
            triage_message: Triage recommendation
            summary: Optional summary text
        
        Returns:
            Updated conversation
        """
        conversation = self.get_by_id_or_raise(conversation_id)
        
        conversation.is_complete = "true"
        conversation.completed_at = datetime.utcnow()
        conversation.triage_level = triage_level
        conversation.triage_message = triage_message
        
        if summary:
            conversation.bulleted_summary = summary
        
        self.db.flush()
        
        logger.info(
            f"Completed conversation {conversation_id}",
            extra={"triage_level": triage_level}
        )
        
        return conversation
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def count_by_triage_level(
        self,
        since: Optional[datetime] = None
    ) -> dict:
        """
        Get count of conversations by triage level.
        
        Args:
            since: Only count conversations after this time
        
        Returns:
            Dictionary of triage_level -> count
        """
        query = self.db.query(
            Conversation.triage_level,
            func.count(Conversation.uuid)
        ).group_by(Conversation.triage_level)
        
        if since:
            query = query.filter(Conversation.created_at >= since)
        
        results = query.all()
        
        return {level or "none": count for level, count in results}
    
    def count_patient_conversations(self, patient_uuid: UUID) -> int:
        """Get count of conversations for a patient."""
        return self.db.query(Conversation).filter(
            Conversation.patient_uuid == patient_uuid
        ).count()





