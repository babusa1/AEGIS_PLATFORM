"""
Analytics Models - Doctor API
=============================

Models for clinical analytics, time-series data, and reporting.

Tables:
- symptom_time_series: Time-series symptom data for analytics
- treatment_events: Treatment/chemo events for timeline overlays
- physician_reports: Weekly report metadata
- audit_logs: HIPAA-compliant access logging

These models power the Doctor Dashboard analytics features.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, Date, Integer, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.base import DoctorBase, TimestampMixin


class SymptomTimeSeries(DoctorBase, TimestampMixin):
    """
    Time-series symptom data for clinical analytics.
    
    Stores every symptom event (not just latest values) to power:
    - Timeline charts
    - Severity ranking
    - Trend detection
    - Weekly analytics
    
    Attributes:
        id: UUID primary key
        patient_id: Reference to the patient
        symptom_id: Identifier for the symptom type
        severity: mild, moderate, severe, urgent
        recorded_at: When the symptom was recorded
        source_session_id: Reference to the chat session
    """
    
    __tablename__ = 'symptom_time_series'
    __table_args__ = (
        Index('idx_symptom_patient_time', 'patient_id', 'recorded_at'),
        Index('idx_symptom_severity', 'severity'),
        {'comment': 'Time-series symptom data for analytics'}
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique record identifier"
    )
    
    # Patient reference
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the patient"
    )
    
    # Symptom data
    symptom_id = Column(
        String(100),
        nullable=False,
        comment="Symptom identifier (e.g., 'fever', 'nausea')"
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment="Severity level: mild, moderate, severe, urgent"
    )
    
    # Timing
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the symptom was recorded"
    )
    
    # Source tracking
    source_session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Reference to the chat session that generated this record"
    )
    
    # Additional context
    notes = Column(
        Text,
        nullable=True,
        comment="Additional notes about the symptom"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SymptomTimeSeries(patient={self.patient_id}, "
            f"symptom={self.symptom_id}, severity={self.severity})>"
        )
    
    @property
    def severity_numeric(self) -> int:
        """Convert severity to numeric for charting."""
        mapping = {'mild': 1, 'moderate': 2, 'severe': 3, 'urgent': 4}
        return mapping.get(self.severity, 0)


class TreatmentEvent(DoctorBase, TimestampMixin):
    """
    Treatment and chemotherapy events for timeline overlays.
    
    Used to correlate symptom patterns with treatment events:
    - Chemo start/end
    - Cycle start/end
    - Regimen changes
    
    Attributes:
        id: UUID primary key
        patient_id: Reference to the patient
        event_type: Type of treatment event
        event_date: When the event occurred
        metadata: Additional event details (drug name, cycle number, etc.)
    """
    
    __tablename__ = 'treatment_events'
    __table_args__ = (
        Index('idx_treatment_patient_date', 'patient_id', 'event_date'),
        {'comment': 'Treatment events for timeline overlays'}
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique event identifier"
    )
    
    # Patient reference
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the patient"
    )
    
    # Event details
    event_type = Column(
        String(50),
        nullable=False,
        comment="Event type: chemo_start, chemo_end, cycle_start, cycle_end, regimen_change"
    )
    
    event_date = Column(
        Date,
        nullable=False,
        comment="Date of the event"
    )
    
    # Additional metadata (named event_metadata to avoid SQLAlchemy reserved name)
    event_metadata = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional event details (drug name, cycle number, etc.)"
    )
    
    def __repr__(self) -> str:
        return (
            f"<TreatmentEvent(patient={self.patient_id}, "
            f"type={self.event_type}, date={self.event_date})>"
        )


class PhysicianReport(DoctorBase, TimestampMixin):
    """
    Weekly physician report metadata.
    
    Stores metadata about generated weekly reports.
    The actual PDF is stored in S3.
    
    Attributes:
        id: UUID primary key
        physician_id: Reference to the physician
        report_week_start: Start of the report week
        report_week_end: End of the report week
        generated_at: When the report was generated
        report_s3_path: S3 path to the PDF
    """
    
    __tablename__ = 'physician_reports'
    __table_args__ = (
        Index('idx_report_physician_week', 'physician_id', 'report_week_start'),
        {'comment': 'Weekly physician report metadata'}
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique report identifier"
    )
    
    # Physician reference
    physician_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the physician"
    )
    
    # Report period
    report_week_start = Column(
        Date,
        nullable=False,
        comment="Start of the report week"
    )
    
    report_week_end = Column(
        Date,
        nullable=False,
        comment="End of the report week"
    )
    
    # Generation details
    generated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        comment="When the report was generated"
    )
    
    # Storage
    report_s3_path = Column(
        Text,
        nullable=False,
        comment="S3 path to the PDF report"
    )
    
    # Report contents summary
    patient_count = Column(
        Integer,
        nullable=True,
        comment="Number of patients in the report"
    )
    
    alert_count = Column(
        Integer,
        nullable=True,
        comment="Number of alerts in the report"
    )
    
    def __repr__(self) -> str:
        return (
            f"<PhysicianReport(physician={self.physician_id}, "
            f"week={self.report_week_start} to {self.report_week_end})>"
        )


class AuditLog(DoctorBase):
    """
    HIPAA-compliant audit logging.
    
    Tracks all access to patient data for compliance.
    
    Attributes:
        id: UUID primary key
        user_id: Who accessed the data
        user_role: Role of the user (physician, staff)
        action: What action was performed
        entity_type: Type of data accessed
        entity_id: ID of the specific record
        accessed_at: When the access occurred
    """
    
    __tablename__ = 'audit_logs'
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'accessed_at'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        {'comment': 'HIPAA-compliant access audit logs'}
    )
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique log entry identifier"
    )
    
    # User information
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the user who performed the action"
    )
    
    user_role = Column(
        String(50),
        nullable=False,
        comment="Role of the user: physician, staff, admin"
    )
    
    # Action details
    action = Column(
        String(100),
        nullable=False,
        comment="Action performed: view_patient, view_dashboard, download_report, etc."
    )
    
    entity_type = Column(
        String(50),
        nullable=True,
        comment="Type of entity accessed: patient, conversation, diary, report"
    )
    
    entity_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the specific entity accessed"
    )
    
    # Metadata
    ip_address = Column(
        String(50),
        nullable=True,
        comment="IP address of the request"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string"
    )
    
    # Additional context (named audit_metadata to avoid SQLAlchemy reserved name)
    audit_metadata = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional context about the action"
    )
    
    # Timing
    accessed_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        comment="When the action was performed"
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(user={self.user_id}, action={self.action}, "
            f"entity={self.entity_type}/{self.entity_id})>"
        )



