"""
Education Module Database Models.

This module implements the complete education schema as specified:
- symptoms: Catalog of all symptom definitions
- education_documents: Clinician-approved education content
- disclaimers: Mandatory disclaimer text
- rule_evaluations: Tracks which rules fired and why
- patient_summaries: Immutable patient-facing summaries
- medications_tried: Medications attempted during sessions
- education_delivery_log: Audit trail of what patient saw
- education_access_log: Tracks education tab access

Design Principles:
- No unstructured AI data
- No generated content stored
- All education content traceable to clinician source
- Full auditability
- Immutable summaries
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Boolean,
    Text,
    Float,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum

from db.base import Base


# =============================================================================
# ENUMS
# =============================================================================

class SymptomCategory(str, enum.Enum):
    """Categories of symptoms."""
    EMERGENCY = "emergency"
    COMMON = "common"
    OTHER = "other"


class SessionStatus(str, enum.Enum):
    """Status of a symptom session."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class TriageSeverity(str, enum.Enum):
    """Severity levels from rule evaluation."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    URGENT = "urgent"


class DocumentStatus(str, enum.Enum):
    """Status of education documents."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class MedicationEffectiveness(str, enum.Enum):
    """Effectiveness of medication tried."""
    NONE = "none"
    PARTIAL = "partial"
    HELPED = "helped"


# =============================================================================
# SYMPTOMS CATALOG
# =============================================================================

class Symptom(Base):
    """
    Single source for all symptom definitions.
    
    This table stores the symptom catalog that maps to the
    rule-based symptom checker definitions.
    
    Schema:
        code VARCHAR(20) PRIMARY KEY  -- e.g. BLEED-103
        name VARCHAR(100)
        category VARCHAR(100)
        active BOOLEAN DEFAULT true
    """
    __tablename__ = "symptoms"
    
    code = Column(String(20), primary_key=True)  # e.g., BLEED-103, NAUSEA-101
    name = Column(String(100), nullable=False)
    category = Column(
        String(100),
        default=SymptomCategory.COMMON.value,
        nullable=False,
    )
    description = Column(Text)
    
    # Display settings
    display_order = Column(Integer, default=0)
    icon = Column(String(50))  # Icon identifier for UI
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    education_documents = relationship("EducationDocument", back_populates="symptom")
    rule_evaluations = relationship("RuleEvaluation", back_populates="symptom")


# =============================================================================
# SYMPTOM SESSIONS
# =============================================================================

class SymptomSession(Base):
    """
    Tracks each chatbot interaction/symptom session.
    
    This extends the existing conversations concept with
    structured session tracking for education delivery.
    
    Schema:
        id UUID PRIMARY KEY
        patient_id UUID REFERENCES patients(id)
        started_at TIMESTAMP
        completed_at TIMESTAMP
        status VARCHAR(30) -- IN_PROGRESS, COMPLETED
        created_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "symptom_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="References patient_info.uuid"
    )
    
    # Link to existing conversation if applicable
    conversation_uuid = Column(UUID(as_uuid=True), index=True)
    
    # Session timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Status
    status = Column(
        String(30),
        default=SessionStatus.IN_PROGRESS.value,
        nullable=False,
        index=True,
    )
    
    # Session data (denormalized for quick access)
    selected_symptoms = Column(JSONB)  # List of symptom codes
    highest_severity = Column(String(20))  # Highest severity level
    escalation_triggered = Column(Boolean, default=False)
    
    # Summary (generated at completion)
    summary_generated = Column(Boolean, default=False)
    education_delivered = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rule_evaluations = relationship(
        "RuleEvaluation",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    medications_tried = relationship(
        "MedicationTried",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    education_deliveries = relationship(
        "EducationDeliveryLog",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    summary = relationship(
        "PatientSummary",
        back_populates="session",
        uselist=False,
    )


# =============================================================================
# RULE EVALUATIONS
# =============================================================================

class RuleEvaluation(Base):
    """
    Stores which rules fired and why.
    
    This is the audit trail for symptom checker decisions.
    
    Schema:
        id UUID PRIMARY KEY
        session_id UUID REFERENCES symptom_sessions(id)
        symptom_code VARCHAR(20) REFERENCES symptoms(code)
        rule_id VARCHAR(30) -- URG-103
        condition_met BOOLEAN
        severity VARCHAR(20) -- mild/moderate/urgent
        escalation BOOLEAN
        evaluated_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "rule_evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("symptom_sessions.id"),
        nullable=False,
        index=True,
    )
    symptom_code = Column(
        String(20),
        ForeignKey("symptoms.code"),
        nullable=False,
        index=True,
    )
    
    # Rule identification
    rule_id = Column(String(50), nullable=False)  # e.g., URG-103, MOD-201
    rule_name = Column(String(255))  # Human-readable rule name
    
    # Evaluation result
    condition_met = Column(Boolean, nullable=False)
    severity = Column(String(20))  # mild, moderate, urgent
    escalation = Column(Boolean, default=False)
    
    # Context (what triggered this)
    trigger_answers = Column(JSONB)  # Answers that triggered this rule
    triage_message = Column(Text)  # Message shown to patient
    
    # Timing
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("SymptomSession", back_populates="rule_evaluations")
    symptom = relationship("Symptom", back_populates="rule_evaluations")


# =============================================================================
# EDUCATION DOCUMENTS (Critical Table)
# =============================================================================

class EducationDocument(Base):
    """
    Stores clinician-approved education content.
    
    This table prevents hallucination by ensuring:
    - inline_text is copied verbatim from approved docs
    - No NULL source_document_id
    - Only status='active' is rendered
    
    Schema:
        id UUID PRIMARY KEY
        symptom_code VARCHAR(20) REFERENCES symptoms(code)
        title VARCHAR(255)
        inline_text TEXT
        s3_pdf_path TEXT
        s3_text_path TEXT
        source_document_id VARCHAR(100)
        version INTEGER
        approved_by VARCHAR(255)
        approved_date DATE
        status VARCHAR(20) -- active/inactive
        priority INTEGER DEFAULT 0
        created_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "education_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symptom_code = Column(
        String(20),
        ForeignKey("symptoms.code"),
        nullable=False,
        index=True,
    )
    
    # Document identification
    title = Column(String(255), nullable=False)
    document_type = Column(String(50))  # symptom_specific, care_team_handout, general
    
    # Content - CRITICAL: inline_text is copied verbatim, never generated
    inline_text = Column(Text, nullable=False)  # 4-6 bullets, Grade 6-8 reading level
    
    # S3 Storage paths
    s3_pdf_path = Column(Text, nullable=False)  # e.g., symptoms/bleeding/bleeding_v1.pdf
    s3_text_path = Column(Text)  # Text version for inline content
    
    # Audit trail - REQUIRED
    source_document_id = Column(String(100), nullable=False)  # Links to original source
    version = Column(Integer, nullable=False, default=1)
    
    # Approval tracking
    approved_by = Column(String(255), nullable=False)
    approved_date = Column(Date, nullable=False)
    
    # Status
    status = Column(
        String(20),
        default=DocumentStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    
    # Display ordering
    priority = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    symptom = relationship("Symptom", back_populates="education_documents")
    delivery_logs = relationship("EducationDeliveryLog", back_populates="education_document")
    access_logs = relationship("EducationAccessLog", back_populates="education_document")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("source_document_id IS NOT NULL", name="check_source_required"),
        Index("ix_education_symptom_status", "symptom_code", "status"),
    )


# =============================================================================
# MANDATORY DISCLAIMERS
# =============================================================================

class Disclaimer(Base):
    """
    Mandatory disclaimer text.
    
    Stored once in DB, referenced by ID.
    Cannot be edited by frontend or engineers.
    Displayed every time education is shown.
    
    Schema:
        id VARCHAR(50) PRIMARY KEY
        text TEXT NOT NULL
        active BOOLEAN DEFAULT true
    """
    __tablename__ = "disclaimers"
    
    id = Column(String(50), primary_key=True)  # e.g., STD-DISCLAIMER-001
    text = Column(Text, nullable=False)
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Versioning
    version = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# CARE TEAM HANDOUT
# =============================================================================

class CareTeamHandout(Base):
    """
    Care Team Handout - guaranteed delivery with every education response.
    
    This is a special document that:
    - Is always attached to every education response
    - Is always available in the education tab
    - Has its own inline summary bullets + full PDF
    """
    __tablename__ = "care_team_handouts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content
    title = Column(String(255), nullable=False, default="Care Team Handout")
    inline_summary = Column(Text, nullable=False)  # Summary bullets
    
    # S3 paths
    s3_pdf_path = Column(Text, nullable=False)
    s3_text_path = Column(Text)
    
    # Version control (no overwrite)
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Audit
    source_document_id = Column(String(100), nullable=False)
    approved_by = Column(String(255), nullable=False)
    approved_date = Column(Date, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# PATIENT SUMMARY STORAGE (Immutable)
# =============================================================================

class PatientSummary(Base):
    """
    Immutable patient-facing summary.
    
    Generated from templates, not AI.
    Patient can add optional note but cannot edit system text.
    
    Schema:
        id UUID PRIMARY KEY
        session_id UUID REFERENCES symptom_sessions(id)
        summary_text TEXT NOT NULL
        patient_note TEXT
        escalation BOOLEAN
        locked BOOLEAN DEFAULT true
        created_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "patient_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("symptom_sessions.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="References patient_info.uuid"
    )
    
    # System-generated summary (immutable)
    summary_text = Column(Text, nullable=False)
    
    # Patient optional note (max 300 chars enforced at API level)
    patient_note = Column(Text)
    
    # Escalation status
    escalation = Column(Boolean, default=False)
    
    # Lock status - ALWAYS TRUE (prevents modification)
    locked = Column(Boolean, default=True, nullable=False)
    
    # Template used for generation (for audit)
    template_id = Column(String(50))
    
    # Provider visibility
    visible_to_provider = Column(Boolean, default=True)
    provider_viewed_at = Column(DateTime(timezone=True))
    provider_id = Column(UUID(as_uuid=True))  # Which provider viewed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("SymptomSession", back_populates="summary")


# =============================================================================
# MEDICATIONS TRIED
# =============================================================================

class MedicationTried(Base):
    """
    Medications attempted during symptom session.
    
    Tracks what the patient tried and its effectiveness.
    
    Schema:
        id UUID PRIMARY KEY
        session_id UUID REFERENCES symptom_sessions(id)
        medication_name VARCHAR(255)
        effectiveness VARCHAR(50) -- none/partial/helped
        recorded_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "medications_tried"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("symptom_sessions.id"),
        nullable=False,
        index=True,
    )
    
    # Medication info
    medication_name = Column(String(255), nullable=False)
    medication_category = Column(String(50))  # antiemetic, pain, etc.
    
    # Effectiveness
    effectiveness = Column(
        String(50),
        default=MedicationEffectiveness.NONE.value,
    )
    
    # Timing
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship back to session
    session = relationship("SymptomSession", back_populates="medications_tried")


# =============================================================================
# EDUCATION DELIVERY LOG (Audit)
# =============================================================================

class EducationDeliveryLog(Base):
    """
    Tracks what education the patient saw.
    
    This is the audit trail for education delivery.
    
    Schema:
        id UUID PRIMARY KEY
        session_id UUID REFERENCES symptom_sessions(id)
        education_document_id UUID REFERENCES education_documents(id)
        delivered_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "education_delivery_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("symptom_sessions.id"),
        nullable=False,
        index=True,
    )
    education_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("education_documents.id"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # Delivery details
    disclaimer_id = Column(String(50))  # Which disclaimer was shown
    care_team_handout_included = Column(Boolean, default=True)
    
    # Tracking
    delivered_at = Column(DateTime(timezone=True), server_default=func.now())
    viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime(timezone=True))
    
    # Relationships
    session = relationship("SymptomSession", back_populates="education_deliveries")
    education_document = relationship("EducationDocument", back_populates="delivery_logs")


# =============================================================================
# EDUCATION ACCESS LOG (Tab Analytics)
# =============================================================================

class EducationAccessLog(Base):
    """
    Tracks education tab access for analytics.
    
    Optional but recommended for understanding usage patterns.
    
    Schema:
        id UUID PRIMARY KEY
        patient_id UUID REFERENCES patients(id)
        education_document_id UUID REFERENCES education_documents(id)
        accessed_at TIMESTAMP DEFAULT now()
    """
    __tablename__ = "education_access_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    education_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("education_documents.id"),
        nullable=False,
        index=True,
    )
    
    # Access type
    access_type = Column(String(50))  # view, download, link_click
    
    # Context
    source = Column(String(50))  # education_tab, post_session, notification
    
    # Timing
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    duration_seconds = Column(Integer)  # How long they viewed (if tracked)
    
    # Relationships
    education_document = relationship("EducationDocument", back_populates="access_logs")


# =============================================================================
# SEED DATA FUNCTIONS
# =============================================================================

def get_default_disclaimer() -> dict:
    """
    Get the default disclaimer that must be seeded.
    
    This is the immutable text shown with every education delivery.
    """
    return {
        "id": "STD-DISCLAIMER-001",
        "text": (
            "This information is for education only and does not replace medical advice. "
            "Always follow instructions from your oncology care team."
        ),
        "active": True,
        "version": 1,
    }


def get_symptom_catalog() -> list:
    """
    Get the symptom catalog to seed from existing symptom definitions.
    
    This maps the Python symptom definitions to database records.
    """
    return [
        # Emergency symptoms
        {"code": "FEVER-101", "name": "Fever", "category": "emergency"},
        {"code": "BLEED-103", "name": "Bleeding", "category": "emergency"},
        {"code": "BREATH-102", "name": "Shortness of Breath", "category": "emergency"},
        
        # Common symptoms
        {"code": "NAUSEA-101", "name": "Nausea", "category": "common"},
        {"code": "VOMIT-101", "name": "Vomiting", "category": "common"},
        {"code": "DIARRHEA-101", "name": "Diarrhea", "category": "common"},
        {"code": "CONSTIPATION-101", "name": "Constipation", "category": "common"},
        {"code": "FATIGUE-101", "name": "Fatigue", "category": "common"},
        {"code": "PAIN-101", "name": "Pain", "category": "common"},
        {"code": "APPETITE-101", "name": "Loss of Appetite", "category": "common"},
        {"code": "MOUTH-101", "name": "Mouth Sores", "category": "common"},
        
        # Other symptoms
        {"code": "NEURO-101", "name": "Neuropathy", "category": "other"},
        {"code": "SKIN-101", "name": "Skin Changes", "category": "other"},
        {"code": "SLEEP-101", "name": "Sleep Problems", "category": "other"},
        {"code": "MOOD-101", "name": "Mood Changes", "category": "other"},
        {"code": "COUGH-101", "name": "Cough", "category": "other"},
        {"code": "SWELLING-101", "name": "Swelling", "category": "other"},
        {"code": "WEIGHT-101", "name": "Weight Changes", "category": "other"},
    ]



