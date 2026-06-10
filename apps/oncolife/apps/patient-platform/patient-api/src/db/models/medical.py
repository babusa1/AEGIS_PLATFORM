"""
Medical Record Models for OncoLife.

This module defines models for:
- ChemoSession: Chemotherapy session records
- ChemoSymptom: Symptoms recorded during/after chemo
- DiaryEntry: Patient diary entries
- ConversationSummary: AI-generated conversation summaries

These models track the patient's treatment journey and symptoms.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Integer, Boolean, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base, TimestampMixin


class ChemoSession(Base, TimestampMixin):
    """
    Represents a chemotherapy session.
    
    Tracks chemotherapy treatments including:
    - Treatment details (drugs, dosages)
    - Session timing and location
    - Side effects and observations
    
    Attributes:
        uuid: Unique session identifier
        patient_uuid: Reference to the patient
        session_date: Date of the session
        cycle_number: Treatment cycle number
        treatment_protocol: Protocol name/ID
        drugs_administered: JSON list of drugs and dosages
        notes: Clinical notes
    """
    
    __tablename__ = "chemo_sessions"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Patient reference
    patient_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Session details
    session_date = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Date and time of the session"
    )
    cycle_number = Column(
        Integer,
        nullable=True,
        doc="Treatment cycle number (1, 2, 3, etc.)"
    )
    day_in_cycle = Column(
        Integer,
        nullable=True,
        doc="Day within the cycle"
    )
    
    # Treatment information
    treatment_protocol = Column(
        String(100),
        nullable=True,
        doc="Protocol name (e.g., FOLFOX, CHOP)"
    )
    drugs_administered = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="List of drugs with dosages"
    )
    
    # Location
    location = Column(
        String(200),
        nullable=True,
        doc="Treatment location/facility"
    )
    
    # Status
    status = Column(
        String(50),
        default="scheduled",
        nullable=False,
        doc="Status: scheduled, in_progress, completed, cancelled"
    )
    
    # Clinical notes
    notes = Column(
        Text,
        nullable=True,
        doc="Clinical notes from the session"
    )
    pre_treatment_vitals = Column(
        JSONB,
        nullable=True,
        doc="Vitals before treatment"
    )
    post_treatment_vitals = Column(
        JSONB,
        nullable=True,
        doc="Vitals after treatment"
    )
    
    # Relationships
    patient = relationship("Patient", back_populates="chemo_sessions")
    symptoms = relationship(
        "ChemoSymptom",
        back_populates="chemo_session",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return (
            f"<ChemoSession(uuid={self.uuid}, "
            f"patient={self.patient_uuid}, "
            f"date={self.session_date}, "
            f"cycle={self.cycle_number})>"
        )


class ChemoSymptom(Base, TimestampMixin):
    """
    Symptoms reported during or after chemotherapy.
    
    Tracks patient-reported symptoms with:
    - Symptom type and severity
    - Timing relative to treatment
    - Duration and management
    """
    
    __tablename__ = "chemo_symptoms"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # References
    chemo_session_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("chemo_sessions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    patient_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Symptom details
    symptom_code = Column(
        String(20),
        nullable=False,
        doc="Symptom code (e.g., NAU-203, VOM-204)"
    )
    symptom_name = Column(
        String(100),
        nullable=False,
        doc="Symptom name"
    )
    severity = Column(
        String(20),
        nullable=True,
        doc="Severity: mild, moderate, severe"
    )
    
    # Timing
    onset_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When symptom started"
    )
    days_after_treatment = Column(
        Integer,
        nullable=True,
        doc="Days after chemo when symptom appeared"
    )
    duration_hours = Column(
        Float,
        nullable=True,
        doc="How long the symptom lasted"
    )
    
    # Management
    medication_taken = Column(
        String(200),
        nullable=True,
        doc="Medication taken for symptom"
    )
    medication_helped = Column(
        Boolean,
        nullable=True,
        doc="Whether medication was effective"
    )
    
    # Notes
    notes = Column(
        Text,
        nullable=True,
        doc="Additional notes"
    )
    
    # Relationships
    chemo_session = relationship("ChemoSession", back_populates="symptoms")
    
    def __repr__(self) -> str:
        return (
            f"<ChemoSymptom(uuid={self.uuid}, "
            f"symptom='{self.symptom_name}', "
            f"severity='{self.severity}')>"
        )


class DiaryEntry(Base, TimestampMixin):
    """
    Patient diary entry for daily health tracking.
    
    Allows patients to record:
    - Daily feelings and symptoms
    - Activities and sleep
    - Medication adherence
    - General notes
    """
    
    __tablename__ = "diary_entries"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Patient reference
    patient_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Entry details
    entry_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date of the diary entry"
    )
    
    # Overall feeling
    overall_feeling = Column(
        String(20),
        nullable=True,
        doc="Overall feeling: great, good, okay, bad, terrible"
    )
    energy_level = Column(
        Integer,
        nullable=True,
        doc="Energy level 1-10"
    )
    pain_level = Column(
        Integer,
        nullable=True,
        doc="Pain level 0-10"
    )
    
    # Sleep tracking
    sleep_hours = Column(
        Float,
        nullable=True,
        doc="Hours of sleep"
    )
    sleep_quality = Column(
        String(20),
        nullable=True,
        doc="Sleep quality: poor, fair, good, excellent"
    )
    
    # Symptoms
    symptoms_today = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="List of symptoms experienced"
    )
    
    # Medications
    medications_taken = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="List of medications taken"
    )
    
    # Activities
    activities = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="Activities performed"
    )
    
    # Notes
    notes = Column(
        Text,
        nullable=True,
        doc="Free-form notes"
    )
    
    # Relationships
    patient = relationship("Patient", back_populates="diary_entries")
    
    def __repr__(self) -> str:
        return (
            f"<DiaryEntry(uuid={self.uuid}, "
            f"patient={self.patient_uuid}, "
            f"date={self.entry_date})>"
        )


class ConversationSummary(Base, TimestampMixin):
    """
    AI-generated summary of a conversation.
    
    Stores structured summaries for care team review,
    including key findings and recommendations.
    """
    
    __tablename__ = "conversation_summaries"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # References
    conversation_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.uuid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    patient_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Summary content
    summary_type = Column(
        String(50),
        default="symptom_check",
        nullable=False,
        doc="Type: symptom_check, follow_up, general"
    )
    
    # Key findings
    chief_complaints = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="Primary complaints/symptoms"
    )
    symptoms_reported = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="All symptoms reported"
    )
    
    # Triage
    triage_level = Column(
        String(50),
        nullable=True,
        doc="Final triage level"
    )
    triage_reasons = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="Reasons for triage level"
    )
    
    # Recommendations
    recommendations = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="Care recommendations"
    )
    follow_up_needed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether follow-up is needed"
    )
    follow_up_timeframe = Column(
        String(50),
        nullable=True,
        doc="Suggested follow-up timeframe"
    )
    
    # Narrative summaries
    brief_summary = Column(
        Text,
        nullable=True,
        doc="One-paragraph summary"
    )
    detailed_summary = Column(
        Text,
        nullable=True,
        doc="Detailed narrative summary"
    )
    
    # Review status
    reviewed_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Staff member who reviewed"
    )
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When summary was reviewed"
    )
    review_notes = Column(
        Text,
        nullable=True,
        doc="Notes from reviewer"
    )
    
    def __repr__(self) -> str:
        return (
            f"<ConversationSummary(uuid={self.uuid}, "
            f"conversation={self.conversation_uuid}, "
            f"triage='{self.triage_level}')>"
        )





