"""
Conversation Service for Symptom Checker Business Logic.

This service handles:
- Conversation lifecycle management
- Integration with the symptom checker engine
- Message processing and routing
- Triage determination

This is the main service that orchestrates the rule-based
symptom checker conversations.

Usage:
    from services import ConversationService
    
    service = ConversationService(db)
    conversation, is_new = service.get_or_create_session(patient_id)
    response = service.process_message(conversation.uuid, user_message)
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from db.models import Conversation, Message
from db.repositories import ConversationRepository
from services.base import BaseService
from core.exceptions import NotFoundException, ValidationException
from core.logging import get_logger

# Import symptom checker engine
from routers.chat.symptom_checker import SymptomCheckerEngine

logger = get_logger(__name__)


class ConversationService(BaseService):
    """
    Service for conversation and symptom checker operations.
    
    Manages the full lifecycle of symptom checker conversations,
    from session creation to triage determination.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the conversation service.
        
        Args:
            db: Database session
        """
        super().__init__(db)
        self.conversation_repo = ConversationRepository(db)
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def get_or_create_session(
        self,
        patient_uuid: UUID
    ) -> Tuple[Conversation, bool]:
        """
        Get or create a chat session for a patient.
        
        Returns the active conversation if one exists,
        otherwise creates a new one.
        
        Args:
            patient_uuid: Patient UUID
        
        Returns:
            Tuple of (conversation, is_new_session)
        """
        conversation, is_new = self.conversation_repo.get_or_create_active_conversation(
            patient_uuid
        )
        
        if is_new:
            # Initialize the symptom checker engine
            engine = SymptomCheckerEngine()
            engine_state = engine.to_dict()
            
            # Save initial engine state
            conversation.engine_state = engine_state
            
            # Add initial greeting message
            greeting = self._get_initial_greeting()
            self.conversation_repo.add_message(
                conversation_id=conversation.uuid,
                sender="assistant",
                content=greeting["content"],
                message_type=greeting["type"],
                structured_data=greeting.get("structured_data")
            )
            
            logger.info(
                f"Created new conversation for patient {patient_uuid}",
                extra={"conversation_id": str(conversation.uuid)}
            )
        
        return conversation, is_new
    
    def get_conversation(self, conversation_id: UUID) -> Conversation:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: Conversation UUID
        
        Returns:
            Conversation with messages
        
        Raises:
            NotFoundException: If conversation doesn't exist
        """
        conversation = self.conversation_repo.get_with_messages(conversation_id)
        if not conversation:
            raise NotFoundException(
                f"Conversation with ID {conversation_id} not found"
            )
        return conversation
    
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
        return self.conversation_repo.get_patient_conversations(
            patient_uuid, skip=skip, limit=limit
        )
    
    # =========================================================================
    # MESSAGE PROCESSING
    # =========================================================================
    
    def process_message(
        self,
        conversation_id: UUID,
        user_input: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        This is the main entry point for handling user input
        in the symptom checker flow.
        
        Args:
            conversation_id: Conversation UUID
            user_input: User's message/selection
            message_type: Type of input (text, button_response, etc.)
        
        Returns:
            Response dictionary with message and metadata
        """
        # Get conversation
        conversation = self.get_conversation(conversation_id)
        
        # Restore engine state
        engine = SymptomCheckerEngine.from_dict(
            conversation.engine_state or {}
        )
        
        # Save user message
        self.conversation_repo.add_message(
            conversation_id=conversation_id,
            sender="user",
            content=user_input,
            message_type=message_type
        )
        
        # Process input through engine
        result = engine.process_input(user_input)
        
        # Save engine state
        conversation.engine_state = engine.to_dict()
        
        # Update conversation state
        conversation.conversation_state = engine.state
        conversation.symptom_list = engine.selected_symptoms
        
        # Create assistant response message
        self.conversation_repo.add_message(
            conversation_id=conversation_id,
            sender="assistant",
            content=result["message"],
            message_type=result.get("type", "text"),
            structured_data=result.get("structured_data")
        )
        
        # Check if conversation is complete
        if result.get("is_complete"):
            self._complete_conversation(
                conversation,
                triage_level=result.get("triage_level", "none"),
                triage_message=result.get("triage_message", "")
            )
        
        self.flush()
        
        return {
            "message": result["message"],
            "type": result.get("type", "text"),
            "structured_data": result.get("structured_data"),
            "is_complete": result.get("is_complete", False),
            "triage_level": result.get("triage_level"),
            "triage_message": result.get("triage_message"),
        }
    
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
            List of messages
        """
        # Verify conversation exists
        self.get_conversation(conversation_id)
        
        return self.conversation_repo.get_messages(
            conversation_id, skip=skip, limit=limit
        )
    
    # =========================================================================
    # TRIAGE AND ALERTS
    # =========================================================================
    
    def get_emergency_conversations(
        self,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Get conversations with emergency triage.
        
        Args:
            since: Filter to conversations after this time
            limit: Maximum results
        
        Returns:
            List of emergency conversations
        """
        return self.conversation_repo.get_emergency_conversations(
            since=since, limit=limit
        )
    
    def get_care_team_alerts(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Get conversations requiring care team notification.
        
        Args:
            since: Filter to conversations after this time
            limit: Maximum results
        
        Returns:
            List of conversations needing review
        """
        return self.conversation_repo.get_care_team_alerts(
            since=since, limit=limit
        )
    
    def get_triage_statistics(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Get conversation counts by triage level.
        
        Args:
            since: Filter to conversations after this time
        
        Returns:
            Dictionary of triage_level -> count
        """
        return self.conversation_repo.count_by_triage_level(since=since)
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _get_initial_greeting(self) -> Dict[str, Any]:
        """
        Get the initial greeting message for a new conversation.
        
        Returns:
            Message dictionary with content and type
        """
        return {
            "content": (
                "Hello! I'm Ruby, your OncoLife symptom assistant. "
                "I'm here to help you track and report any symptoms you may be experiencing. "
                "How are you feeling today?"
            ),
            "type": "feeling-select",
            "structured_data": {
                "options": [
                    "I'm feeling great",
                    "I'm feeling good", 
                    "I'm feeling okay",
                    "I'm not feeling well",
                    "I'm feeling terrible"
                ]
            }
        }
    
    def _complete_conversation(
        self,
        conversation: Conversation,
        triage_level: str,
        triage_message: str
    ) -> None:
        """
        Mark a conversation as complete.
        
        Args:
            conversation: Conversation to complete
            triage_level: Final triage level
            triage_message: Triage recommendation
        """
        conversation.is_complete = "true"
        conversation.completed_at = datetime.utcnow()
        conversation.triage_level = triage_level
        conversation.triage_message = triage_message
        
        logger.info(
            f"Completed conversation {conversation.uuid}",
            extra={
                "triage_level": triage_level,
                "patient_uuid": str(conversation.patient_uuid)
            }
        )
        
        # Add system message about triage
        if triage_level == "call_911":
            self.conversation_repo.add_message(
                conversation_id=conversation.uuid,
                sender="system",
                content=f"🚨 EMERGENCY: {triage_message}",
                message_type="system"
            )
        elif triage_level == "notify_care_team":
            self.conversation_repo.add_message(
                conversation_id=conversation.uuid,
                sender="system",
                content=f"⚠️ Care Team Alert: {triage_message}",
                message_type="system"
            )





