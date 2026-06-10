"""
Normalized Database Schema for Patient Onboarding.

This module implements the complete schema as specified:
- patients (uses existing patient_info)
- providers (NEW - physician/clinic info)
- oncology_profile (NEW - cancer & treatment details)
- medications (NEW - normalized medication list)
- fax_ingestion_log (NEW - fax processing audit)
- ocr_field_confidence (NEW - per-field OCR confidence)

All tables follow HIPAA compliance requirements with proper
audit trails and encryption considerations.
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
    func,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum

from db.base import Base


# =============================================================================
# ENUMS
# =============================================================================

class MedicationCategory(str, enum.Enum):
    """Categories of medications for oncology patients."""
    CHEMOTHERAPY = "chemotherapy"
    SUPPORTIVE = "supportive"  # e.g., Neulasta, anti-nausea
    IMMUNOTHERAPY = "immunotherapy"
    TARGETED_THERAPY = "targeted_therapy"
    HORMONE_THERAPY = "hormone_therapy"
    OTHER = "other"


class OcrFieldStatus(str, enum.Enum):
    """Status of an OCR-extracted field."""
    ACCEPTED = "accepted"  # Confidence >= threshold
    REQUIRES_REVIEW = "requires_review"  # Confidence < threshold
    MANUALLY_VERIFIED = "manually_verified"  # Human verified
    REJECTED = "rejected"  # Determined to be incorrect
    CORRECTED = "corrected"  # Human corrected


class FaxProcessingStatus(str, enum.Enum):
    """Status of fax processing pipeline."""
    RECEIVED = "received"
    DOWNLOADING = "downloading"
    UPLOADED_TO_S3 = "uploaded_to_s3"
    OCR_STARTED = "ocr_started"
    OCR_COMPLETED = "ocr_completed"
    PARSING = "parsing"
    PARSED = "parsed"
    REVIEW_NEEDED = "review_needed"
    APPROVED = "approved"
    PATIENT_CREATED = "patient_created"
    FAILED = "failed"


# =============================================================================
# PROVIDERS TABLE
# =============================================================================

class Provider(Base):
    """
    Healthcare providers (physicians) and their clinic associations.
    
    This table stores the referring physician information extracted
    from referral faxes. Used for:
    - Patient-physician associations
    - Displaying physician info to patients
    - Routing summaries to correct providers
    
    Schema:
        provider_id UUID PRIMARY KEY
        full_name VARCHAR(255)
        clinic_name VARCHAR(255)
        phone VARCHAR(20)
        fax VARCHAR(20)
        created_at TIMESTAMP
    """
    __tablename__ = "providers"
    
    provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Provider identification
    full_name = Column(String(255), nullable=False, index=True)
    npi = Column(String(20), unique=True, index=True)  # National Provider Identifier
    specialty = Column(String(100))  # e.g., "Medical Oncology"
    
    # Clinic/practice information
    clinic_name = Column(String(255), index=True)
    clinic_address = Column(Text)
    clinic_city = Column(String(100))
    clinic_state = Column(String(50))
    clinic_zip = Column(String(20))
    
    # Contact information
    phone = Column(String(20))
    fax = Column(String(20))
    email = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    oncology_profiles = relationship("OncologyProfile", back_populates="provider")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('full_name', 'clinic_name', name='uq_provider_name_clinic'),
    )


# =============================================================================
# ONCOLOGY PROFILE TABLE
# =============================================================================

class OncologyProfile(Base):
    """
    Patient's oncology treatment profile.
    
    Stores cancer diagnosis and treatment information extracted from
    referrals. This data is used for:
    - Symptom checker rule configuration
    - Treatment timeline display
    - Personalized education content
    
    Schema:
        profile_id UUID PRIMARY KEY
        patient_id UUID REFERENCES patients(patient_id)
        cancer_type VARCHAR(255)
        cancer_stage VARCHAR(50)
        line_of_treatment VARCHAR(100)
        chemo_plan_name TEXT
        chemo_start_date DATE
        chemo_end_date DATE
        bmi DECIMAL(4,1)
        created_at TIMESTAMP
    """
    __tablename__ = "oncology_profiles"
    
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Link to patient
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="References patient_info.uuid"
    )
    
    # Link to provider
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("providers.provider_id"),
        index=True,
    )
    
    # Link to referral (source of this data)
    referral_uuid = Column(UUID(as_uuid=True), index=True)
    
    # ==========================================================================
    # CANCER DIAGNOSIS (Patient-Facing)
    # ==========================================================================
    
    cancer_type = Column(String(255), nullable=False)
    cancer_stage = Column(String(50))  # e.g., "IIB", "Stage 3"
    cancer_diagnosis_date = Column(Date)
    cancer_icd10_code = Column(String(20))  # e.g., "C50.912"
    cancer_snomed_code = Column(String(50))  # SNOMED CT code
    
    # ==========================================================================
    # TREATMENT INFORMATION (Patient-Facing)
    # ==========================================================================
    
    line_of_treatment = Column(String(100))  # Neoadjuvant, Adjuvant, Palliative
    treatment_goal = Column(String(100))  # Curative, Palliative
    
    chemo_plan_name = Column(Text)  # e.g., "ddAC → Paclitaxel"
    chemo_regimen_description = Column(Text)  # Full regimen details
    chemo_start_date = Column(Date)
    chemo_end_date = Column(Date)  # Planned end date
    
    current_cycle = Column(Integer)
    total_cycles = Column(Integer)
    
    treatment_department = Column(String(255))
    
    # Appointment tracking (Patient-Facing)
    next_clinic_visit = Column(Date)  # Next scheduled clinic/physician visit
    last_chemo_date = Column(Date)  # Last chemotherapy session date
    
    # ==========================================================================
    # CLINICAL CONTEXT (NOT Displayed to Patient)
    # ==========================================================================
    
    # Vitals at referral time
    bmi = Column(Numeric(4, 1))  # e.g., 24.6
    height_cm = Column(Float)
    weight_kg = Column(Float)
    
    # History (not shown in UI per spec)
    history_of_cancer = Column(Text)
    past_medical_history = Column(Text)
    past_surgical_history = Column(Text)
    
    # Performance status
    ecog_status = Column(Integer)  # 0-4 scale
    
    # ==========================================================================
    # STATUS
    # ==========================================================================
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    provider = relationship("Provider", back_populates="oncology_profiles")
    medications = relationship("Medication", back_populates="oncology_profile")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('ecog_status >= 0 AND ecog_status <= 4', name='check_ecog_range'),
    )


# =============================================================================
# MEDICATIONS TABLE
# =============================================================================

class Medication(Base):
    """
    Normalized medication table for patient treatments.
    
    Stores individual medications with proper categorization:
    - Chemotherapy drugs (required, affects symptom rules)
    - Supportive medications (optional, improves triage)
    
    Non-oncology medications are OUT OF SCOPE per spec.
    
    Schema:
        medication_id UUID PRIMARY KEY
        patient_id UUID REFERENCES patients(patient_id)
        medication_name VARCHAR(255)
        category VARCHAR(50)  -- chemotherapy / supportive
        active BOOLEAN
        created_at TIMESTAMP
    """
    __tablename__ = "medications"
    
    medication_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Link to patient
    patient_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="References patient_info.uuid"
    )
    
    # Link to oncology profile
    oncology_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("oncology_profiles.profile_id"),
        index=True,
    )
    
    # ==========================================================================
    # MEDICATION DETAILS
    # ==========================================================================
    
    medication_name = Column(String(255), nullable=False)
    generic_name = Column(String(255))  # e.g., "paclitaxel" for "Taxol"
    brand_name = Column(String(255))    # e.g., "Taxol"
    
    # Category (per spec: chemotherapy or supportive)
    category = Column(
        String(50),
        nullable=False,
        default=MedicationCategory.CHEMOTHERAPY.value,
        index=True,
    )
    
    # Dosing information (optional)
    dose = Column(String(100))  # e.g., "150 mg"
    dose_unit = Column(String(50))  # e.g., "mg/m2"
    route = Column(String(50))  # e.g., "IV", "Oral"
    frequency = Column(String(100))  # e.g., "Every 2 weeks"
    
    # Treatment timing
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Source tracking
    source = Column(String(50))  # "ocr", "manual", "ehr_import"
    ocr_confidence = Column(Float)  # If extracted via OCR
    
    # Relationships
    oncology_profile = relationship("OncologyProfile", back_populates="medications")


# =============================================================================
# FAX INGESTION LOG TABLE
# =============================================================================

class FaxIngestionLog(Base):
    """
    Audit log for fax ingestion pipeline.
    
    Tracks every fax received from initial reception through
    processing, with full audit trail for HIPAA compliance.
    
    Schema:
        fax_id UUID PRIMARY KEY
        received_at TIMESTAMP
        source_number VARCHAR(20)
        ocr_status VARCHAR(50)
        manual_review_required BOOLEAN
        processed_by VARCHAR(50)
    """
    __tablename__ = "fax_ingestion_log"
    
    fax_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reception details
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    source_number = Column(String(20), index=True)  # Sender fax number
    destination_number = Column(String(20))  # Our fax number
    
    # Provider information
    fax_provider = Column(String(50))  # sinch, twilio, phaxio, etc.
    provider_fax_id = Column(String(255))  # Provider's fax ID
    
    # Document details
    page_count = Column(Integer, default=1)
    file_type = Column(String(50))  # pdf, tiff, etc.
    file_size_bytes = Column(Integer)
    
    # S3 storage
    s3_bucket = Column(String(255))
    s3_key = Column(String(500))
    
    # Processing status
    ocr_status = Column(
        String(50),
        default=FaxProcessingStatus.RECEIVED.value,
        nullable=False,
        index=True,
    )
    ocr_started_at = Column(DateTime(timezone=True))
    ocr_completed_at = Column(DateTime(timezone=True))
    ocr_duration_ms = Column(Integer)  # Processing time
    
    # OCR results
    textract_job_id = Column(String(255))
    overall_confidence = Column(Float)  # Average confidence
    
    # Review status
    manual_review_required = Column(Boolean, default=False, nullable=False)
    manual_review_reason = Column(Text)  # Why review is needed
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))  # User who reviewed
    
    # Processing result
    processed_by = Column(String(50))  # "system" or user ID
    processing_notes = Column(Text)
    error_message = Column(Text)
    
    # Linking
    referral_uuid = Column(UUID(as_uuid=True), index=True)  # Created referral
    patient_uuid = Column(UUID(as_uuid=True), index=True)   # Created patient
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    field_confidences = relationship(
        "OcrFieldConfidence",
        back_populates="fax_log",
        cascade="all, delete-orphan",
    )


# =============================================================================
# OCR FIELD CONFIDENCE TABLE
# =============================================================================

class OcrFieldConfidence(Base):
    """
    Per-field OCR confidence tracking.
    
    Stores confidence scores for each extracted field to enable:
    - Automatic acceptance when confidence >= threshold
    - Manual review flagging when confidence < threshold
    - Audit trail of extraction quality
    
    NEVER auto-correct medical data - only flag for review.
    
    Schema:
        fax_id UUID REFERENCES fax_ingestion_log(fax_id)
        field_name VARCHAR(100)
        extracted_value TEXT
        confidence_score DECIMAL(3,2)
        accepted BOOLEAN
    
    Confidence Thresholds (per spec):
        Patient Name: ≥ 0.95
        DOB: ≥ 0.98
        Phone: ≥ 0.95
        Email: ≥ 0.95
        Cancer Type: ≥ 0.90
        Chemo Plan Name: ≥ 0.90
        Start/End Dates: ≥ 0.95
        Medications: ≥ 0.90
    """
    __tablename__ = "ocr_field_confidence"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to fax
    fax_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fax_ingestion_log.fax_id"),
        nullable=False,
        index=True,
    )
    
    # Field identification
    field_name = Column(String(100), nullable=False, index=True)
    field_category = Column(String(50))  # patient, provider, diagnosis, treatment
    
    # Extracted data
    extracted_value = Column(Text)
    normalized_value = Column(Text)  # Cleaned/formatted version
    
    # Confidence scoring
    confidence_score = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    confidence_threshold = Column(Numeric(5, 4), nullable=False)  # Required threshold
    
    # Status
    status = Column(
        String(50),
        default=OcrFieldStatus.REQUIRES_REVIEW.value,
        nullable=False,
    )
    accepted = Column(Boolean, default=False, nullable=False)
    
    # Review tracking
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))
    corrected_value = Column(Text)  # If manually corrected
    correction_reason = Column(Text)
    
    # Source tracking
    source_page = Column(Integer)  # Which page of the fax
    source_location = Column(JSONB)  # Bounding box coordinates
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fax_log = relationship("FaxIngestionLog", back_populates="field_confidences")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('fax_id', 'field_name', name='uq_fax_field'),
        CheckConstraint(
            'confidence_score >= 0 AND confidence_score <= 1',
            name='check_confidence_range'
        ),
    )


# =============================================================================
# CONFIDENCE THRESHOLDS CONFIGURATION
# =============================================================================

# Per-field confidence thresholds as specified
OCR_CONFIDENCE_THRESHOLDS = {
    # Patient Identifiers (Visible to Patient)
    "patient_name": 0.95,
    "patient_first_name": 0.95,
    "patient_last_name": 0.95,
    "patient_dob": 0.98,
    "patient_phone": 0.95,
    "patient_email": 0.95,
    
    # Provider Information
    "attending_physician_name": 0.90,
    "clinic_name": 0.90,
    
    # Cancer & Treatment (Patient-Facing)
    "cancer_type": 0.90,
    "cancer_staging": 0.85,  # Optional, lower threshold OK
    "line_of_treatment": 0.90,
    "chemo_plan_name": 0.90,
    "chemo_start_date": 0.95,
    "chemo_end_date": 0.95,
    
    # Medications
    "medication_name": 0.90,
    "medication_dose": 0.85,
    
    # Clinical Context (NOT Displayed to Patient)
    "history_of_cancer": 0.75,
    "past_medical_history": 0.75,
    "past_surgical_history": 0.75,
    "bmi": 0.90,
}


def get_confidence_threshold(field_name: str) -> float:
    """
    Get the confidence threshold for a specific field.
    
    Args:
        field_name: Name of the field
        
    Returns:
        Confidence threshold (0.0 to 1.0)
    """
    return OCR_CONFIDENCE_THRESHOLDS.get(field_name, 0.85)  # Default 0.85


def is_field_acceptable(field_name: str, confidence: float) -> bool:
    """
    Check if a field's confidence meets the threshold.
    
    Args:
        field_name: Name of the field
        confidence: OCR confidence score (0.0 to 1.0)
        
    Returns:
        True if confidence >= threshold
    """
    threshold = get_confidence_threshold(field_name)
    return confidence >= threshold



