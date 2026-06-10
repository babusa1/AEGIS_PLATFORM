"""
Patient Questions Model
=======================

Model for "Questions to Ask Doctor" feature.

Patients can:
- Create questions they want to ask their doctor
- Choose whether to share questions with their physician
- Only shared questions are visible in doctor portal

Database Schema:
- patient_questions: Stores patient questions with share_with_physician flag
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import Base, TimestampMixin


class PatientQuestion(Base, TimestampMixin):
    """
    Patient questions to ask their doctor.
    
    Questions are private by default. Patients must explicitly
    choose to share with their physician. Only shared questions
    appear in the doctor portal.
    
    Attributes:
        id: UUID primary key
        patient_uuid: Reference to the patient
        question_text: The question content
        share_with_physician: Whether to share with doctor (default: False)
        is_answered: Whether the question has been addressed
        category: Optional category (symptom, medication, treatment, other)
        created_at: When the question was created
        updated_at: When the question was last modified
    """
    
    __tablename__ = 'patient_questions'
    __table_args__ = (
        Index('ix_patient_questions_patient', 'patient_uuid'),
        Index('ix_patient_questions_shared', 'share_with_physician'),
        {'comment': 'Patient questions to ask their doctor'}
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique question identifier"
    )
    
    # Patient reference
    patient_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the patient"
    )
    
    # Question content
    question_text = Column(
        Text,
        nullable=False,
        comment="The question text"
    )
    
    # Visibility control
    share_with_physician = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether to share with physician (default: private)"
    )
    
    # Status
    is_answered = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the question has been addressed"
    )
    
    # Categorization
    category = Column(
        String(50),
        nullable=True,
        default='other',
        comment="Question category: symptom, medication, treatment, other"
    )
    
    # Soft delete
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )
    
    def __repr__(self) -> str:
        return (
            f"<PatientQuestion(id={self.id}, "
            f"patient={self.patient_uuid}, "
            f"shared={self.share_with_physician})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "patient_uuid": str(self.patient_uuid),
            "question_text": self.question_text,
            "share_with_physician": self.share_with_physician,
            "is_answered": self.is_answered,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



