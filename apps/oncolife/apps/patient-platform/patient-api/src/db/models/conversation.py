"""
Conversation and Message Models for Symptom Checker.

This module defines models for:
- Conversation: Chat sessions with patients
- Message: Individual messages within conversations

These models support the rule-based symptom checker and
track patient-reported symptoms and triage outcomes.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Integer, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """
    Represents a chat conversation/session with a patient.
    
    A conversation tracks:
    - The patient's symptom checker session
    - Current state of the symptom evaluation
    - Collected symptoms and their severity
    - Triage outcomes and recommendations
    
    Attributes:
        uuid: Unique conversation identifier
        patient_uuid: Reference to the patient
        conversation_state: Current state of the conversation
        symptom_list: List of reported symptoms
        severity_list: Severity ratings for symptoms
        engine_state: Complete state of the symptom checker engine
        overall_feeling: Patient's self-reported feeling
        triage_level: Final triage recommendation
    """
    
    __tablename__ = "conversations"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique conversation identifier"
    )
    
    # Patient reference
    patient_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the patient"
    )
    
    # Conversation state tracking
    conversation_state = Column(
        String(50),
        nullable=True,
        default="greeting",
        doc="Current state: greeting, symptom_selection, questioning, complete"
    )
    
    # Symptom tracking
    symptom_list = Column(
        JSONB,
        nullable=True,
        default=list,
        doc="List of reported symptom IDs"
    )
    severity_list = Column(
        JSONB,
        nullable=True,
        default=list,
        doc="Severity ratings for symptoms"
    )
    
    # Symptom checker engine state
    engine_state = Column(
        JSONB,
        nullable=True,
        doc="Complete state of the symptom checker engine"
    )
    
    # Patient self-assessment
    overall_feeling = Column(
        String(50),
        nullable=True,
        doc="Patient's overall feeling: great, good, okay, bad, terrible"
    )
    
    # Triage outcome
    triage_level = Column(
        String(50),
        nullable=True,
        doc="Triage level: call_911, notify_care_team, none"
    )
    triage_message = Column(
        Text,
        nullable=True,
        doc="Triage recommendation message"
    )
    
    # Summary fields (generated after conversation)
    bulleted_summary = Column(
        Text,
        nullable=True,
        doc="Bulleted summary of the conversation"
    )
    longer_summary = Column(
        Text,
        nullable=True,
        doc="Detailed narrative summary"
    )
    
    # Medication tracking
    medication_list = Column(
        JSONB,
        nullable=True,
        default=list,
        doc="List of medications mentioned"
    )
    
    # Completion tracking
    is_complete = Column(
        String(10),
        default="false",
        nullable=True,
        doc="Whether conversation is complete"
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the conversation was completed"
    )
    
    # Relationships
    patient = relationship(
        "Patient",
        back_populates="conversations"
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    @property
    def message_count(self) -> int:
        """Get number of messages in conversation."""
        return len(self.messages) if self.messages else 0
    
    @property
    def is_emergency(self) -> bool:
        """Check if conversation resulted in emergency triage."""
        return self.triage_level == "call_911"
    
    @property
    def requires_care_team(self) -> bool:
        """Check if care team notification is needed."""
        return self.triage_level in ["call_911", "notify_care_team"]
    
    def __repr__(self) -> str:
        return (
            f"<Conversation(uuid={self.uuid}, "
            f"patient={self.patient_uuid}, "
            f"state='{self.conversation_state}')>"
        )


class Message(Base):
    """
    Represents a single message in a conversation.
    
    Messages can be from:
    - user: Patient's responses
    - assistant: Ruby's questions/responses
    - system: System messages (triage alerts, etc.)
    
    Attributes:
        id: Auto-incrementing message ID
        chat_uuid: Reference to the conversation
        sender: Who sent the message (user/assistant/system)
        message_type: Type of message (text, single-select, multi-select, etc.)
        content: Message text content
        structured_data: Additional data (options, selections, etc.)
    """
    
    __tablename__ = "messages"
    
    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing message ID"
    )
    
    # Conversation reference
    chat_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the conversation"
    )
    
    # Message metadata
    sender = Column(
        String(20),
        nullable=False,
        doc="Sender: user, assistant, or system"
    )
    message_type = Column(
        String(50),
        nullable=False,
        default="text",
        doc="Message type: text, single-select, multi-select, button_prompt, etc."
    )
    
    # Message content
    content = Column(
        Text,
        nullable=False,
        doc="Message text content"
    )
    
    # Structured data for interactive messages
    structured_data = Column(
        JSONB,
        nullable=True,
        doc="Additional data: options, selected_options, etc."
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the message was created"
    )
    
    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    @property
    def is_from_user(self) -> bool:
        """Check if message is from user."""
        return self.sender == "user"
    
    @property
    def is_from_assistant(self) -> bool:
        """Check if message is from assistant (Ruby)."""
        return self.sender == "assistant"
    
    @property
    def options(self) -> Optional[List[str]]:
        """Get options from structured data."""
        if self.structured_data and isinstance(self.structured_data, dict):
            return self.structured_data.get("options")
        return None
    
    @property
    def selected_options(self) -> Optional[List[str]]:
        """Get selected options from structured data."""
        if self.structured_data and isinstance(self.structured_data, dict):
            return self.structured_data.get("selected_options")
        return None
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<Message(id={self.id}, "
            f"sender='{self.sender}', "
            f"type='{self.message_type}', "
            f"content='{content_preview}')>"
        )





