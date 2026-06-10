"""
Patient-Specific Models.

This module defines the core Patient model and related entities.
Note: For authentication, see user.py (User model).
This model is for patient-specific data that may exist independently.
"""

import uuid
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base, TimestampMixin


class Patient(Base, TimestampMixin):
    """
    Core Patient model.
    
    This model represents a patient in the system. It may be linked
    to a User for authenticated access, or exist independently for
    patients managed by staff.
    
    Attributes:
        uuid: Unique identifier
        mrn: Medical Record Number (unique within institution)
        first_name: Patient's first name
        last_name: Patient's last name
        email: Contact email
        phone: Contact phone
        date_of_birth: Patient's date of birth
        gender: Patient's gender
        diagnosis_info: JSON object with diagnosis details
        is_active: Whether patient record is active
    """
    
    __tablename__ = "patients"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique patient identifier"
    )
    
    # Medical Record Number - institution-specific ID
    mrn = Column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        doc="Medical Record Number"
    )
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Address information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(50), default="USA", nullable=True)
    
    # Emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Medical information (flexible JSON storage)
    diagnosis_info = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Diagnosis details as JSON"
    )
    
    # Treatment information
    primary_oncologist_uuid = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Reference to primary oncologist"
    )
    care_team_uuid = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Reference to assigned care team"
    )
    
    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether patient record is active"
    )
    
    # Notes
    notes = Column(
        Text,
        nullable=True,
        doc="General notes about the patient"
    )
    
    # Relationships
    conversations = relationship(
        "Conversation",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(Conversation.created_at)"
    )
    chemo_sessions = relationship(
        "ChemoSession",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(ChemoSession.session_date)"
    )
    diary_entries = relationship(
        "DiaryEntry",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(DiaryEntry.entry_date)"
    )
    
    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def primary_diagnosis(self) -> Optional[str]:
        """Get primary diagnosis from diagnosis_info."""
        if isinstance(self.diagnosis_info, dict):
            return self.diagnosis_info.get("primary_diagnosis")
        return None
    
    def __repr__(self) -> str:
        return f"<Patient(uuid={self.uuid}, name='{self.full_name}', mrn='{self.mrn}')>"





