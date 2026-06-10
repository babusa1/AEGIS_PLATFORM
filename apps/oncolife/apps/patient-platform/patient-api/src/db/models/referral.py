"""
Referral and Onboarding Database Models.

These models support the patient onboarding flow:
1. Referral reception (from fax OCR)
2. Patient pre-registration
3. Onboarding status tracking

Tables:
    - patient_referrals: Stores referral data from clinic faxes
    - patient_onboarding_status: Tracks onboarding progress
    - referral_documents: Stores original fax documents
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
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import uuid
import enum

# Use declarative_base for this model to avoid auto tablename generation
# These tables have specific naming requirements
Base = declarative_base()


# =============================================================================
# ENUMS
# =============================================================================

class ReferralStatus(str, enum.Enum):
    """Status of a referral through the processing pipeline."""
    RECEIVED = "received"           # Fax received
    PROCESSING = "processing"       # OCR in progress
    PARSED = "parsed"               # OCR complete, data extracted
    REVIEW_NEEDED = "review_needed" # Manual review required
    PATIENT_CREATED = "patient_created"  # Patient account created
    WELCOME_SENT = "welcome_sent"   # Welcome email/SMS sent
    FAILED = "failed"               # Processing failed
    COMPLETED = "completed"         # Full onboarding complete


class OnboardingStep(str, enum.Enum):
    """Current step in the onboarding flow."""
    NOT_STARTED = "not_started"
    PASSWORD_RESET = "password_reset"
    ACKNOWLEDGEMENT = "acknowledgement"
    TERMS_PRIVACY = "terms_privacy"
    REMINDER_SETUP = "reminder_setup"
    COMPLETED = "completed"


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel."""
    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"


# =============================================================================
# REFERRAL DOCUMENT MODEL
# =============================================================================

class ReferralDocument(Base):
    """
    Stores original fax documents received from clinics.
    
    Each referral can have multiple documents (multi-page fax).
    Documents are stored in S3, this table stores metadata.
    """
    __tablename__ = "referral_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    referral_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patient_referrals.uuid"),
        nullable=False,
        index=True,
    )
    
    # Document storage info
    s3_bucket = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    
    # Document metadata
    file_name = Column(String(255))
    file_type = Column(String(50))  # pdf, tiff, png, etc.
    file_size_bytes = Column(Integer)
    page_count = Column(Integer, default=1)
    
    # OCR processing
    textract_job_id = Column(String(255))  # AWS Textract job ID
    raw_ocr_text = Column(Text)  # Full OCR output
    ocr_confidence = Column(Float)  # Overall confidence score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationship
    referral = relationship("PatientReferral", back_populates="documents")


# =============================================================================
# PATIENT REFERRAL MODEL
# =============================================================================

class PatientReferral(Base):
    """
    Stores parsed referral data from clinic faxes.
    
    This is the main referral record containing all patient data
    extracted from the clinic's EHR referral form.
    """
    __tablename__ = "patient_referrals"
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Processing status
    status = Column(
        String(50),
        default=ReferralStatus.RECEIVED.value,
        nullable=False,
        index=True,
    )
    status_message = Column(Text)  # Error message or notes
    
    # Source information
    fax_number = Column(String(20))  # Fax number received from
    fax_received_at = Column(DateTime(timezone=True))
    referring_clinic = Column(String(255))
    referring_ehr = Column(String(100))  # Epic, Cerner, etc.
    
    # ==========================================================================
    # PATIENT DEMOGRAPHICS (Extracted from referral)
    # ==========================================================================
    
    patient_first_name = Column(String(100))
    patient_last_name = Column(String(100))
    patient_dob = Column(Date)
    patient_sex = Column(String(20))
    patient_email = Column(String(255))
    patient_phone = Column(String(20))
    patient_mrn = Column(String(50))  # Medical Record Number from referring system
    
    # ==========================================================================
    # PHYSICIAN & CLINIC (Extracted from referral)
    # ==========================================================================
    
    attending_physician_name = Column(String(255))
    attending_physician_npi = Column(String(20))  # National Provider Identifier
    clinic_name = Column(String(255))
    clinic_address = Column(Text)
    clinic_phone = Column(String(20))
    clinic_fax = Column(String(20))
    
    # ==========================================================================
    # CANCER & TREATMENT INFORMATION
    # ==========================================================================
    
    cancer_type = Column(String(255))
    cancer_staging = Column(String(100))  # e.g., "IIB", "Stage 3"
    cancer_diagnosis_date = Column(Date)
    
    # Chemotherapy plan
    chemo_plan_name = Column(String(500))
    chemo_regimen = Column(Text)  # Full regimen description
    chemo_start_date = Column(Date)
    chemo_end_date = Column(Date)
    chemo_current_cycle = Column(Integer)
    chemo_total_cycles = Column(Integer)
    treatment_department = Column(String(255))
    treatment_goal = Column(String(100))  # Neoadjuvant, Adjuvant, Palliative
    line_of_treatment = Column(String(100))
    
    # ==========================================================================
    # MEDICAL HISTORY
    # ==========================================================================
    
    history_of_cancer = Column(Text)
    past_medical_history = Column(Text)
    past_surgical_history = Column(Text)
    current_medications = Column(JSONB)  # List of medications
    allergies = Column(Text)
    
    # ==========================================================================
    # VITALS & MEASUREMENTS
    # ==========================================================================
    
    height_cm = Column(Float)
    weight_kg = Column(Float)
    bmi = Column(Float)
    blood_pressure = Column(String(20))
    pulse = Column(Integer)
    temperature_f = Column(Float)
    spo2 = Column(Integer)
    ecog_performance_status = Column(Integer)
    
    # ==========================================================================
    # SOCIAL & BEHAVIORAL
    # ==========================================================================
    
    tobacco_use = Column(String(50))
    alcohol_use = Column(String(100))
    drug_use = Column(String(100))
    social_drivers = Column(JSONB)  # SDOH data
    
    # ==========================================================================
    # LAB RESULTS (Most recent)
    # ==========================================================================
    
    lab_results = Column(JSONB)  # Structured lab data
    
    # ==========================================================================
    # FAMILY HISTORY
    # ==========================================================================
    
    family_history = Column(JSONB)  # List of family conditions
    genetic_testing = Column(Text)  # e.g., "Ambry negative"
    
    # ==========================================================================
    # RAW DATA
    # ==========================================================================
    
    raw_extracted_data = Column(JSONB)  # All extracted fields (for debugging)
    extraction_confidence = Column(Float)  # Overall extraction confidence
    fields_needing_review = Column(JSONB)  # Fields with low confidence
    
    # ==========================================================================
    # PATIENT ACCOUNT LINKING
    # ==========================================================================
    
    patient_uuid = Column(UUID(as_uuid=True), index=True)  # Links to patient_info
    cognito_user_id = Column(String(100))  # AWS Cognito user sub
    temp_password_hash = Column(String(255))  # Hashed temp password (for audit)
    
    # Relationships
    documents = relationship(
        "ReferralDocument",
        back_populates="referral",
        cascade="all, delete-orphan",
    )
    onboarding_status = relationship(
        "PatientOnboardingStatus",
        back_populates="referral",
        uselist=False,
    )


# =============================================================================
# PATIENT ONBOARDING STATUS
# =============================================================================

class PatientOnboardingStatus(Base):
    """
    Tracks patient progress through the onboarding flow.
    
    Flow steps:
    1. Password Reset (mandatory first login)
    2. Acknowledgement Screen (medical disclaimer)
    3. Terms & Privacy Policy acceptance
    4. Reminder Preference setup
    """
    __tablename__ = "patient_onboarding_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    referral_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("patient_referrals.uuid"),
        unique=True,
        index=True,
    )
    patient_uuid = Column(UUID(as_uuid=True), index=True)  # Links to patient_info
    
    # Current step in onboarding
    current_step = Column(
        String(50),
        default=OnboardingStep.NOT_STARTED.value,
        nullable=False,
    )
    
    # ==========================================================================
    # STEP 1: Password Reset
    # ==========================================================================
    
    password_reset_completed = Column(Boolean, default=False)
    password_reset_at = Column(DateTime(timezone=True))
    
    # ==========================================================================
    # STEP 2: Acknowledgement
    # ==========================================================================
    
    # "I understand this tool does not replace my care team or emergency services."
    acknowledgement_completed = Column(Boolean, default=False)
    acknowledgement_text = Column(Text)  # Store the exact text shown
    acknowledgement_at = Column(DateTime(timezone=True))
    acknowledgement_ip = Column(String(50))  # IP address for audit
    
    # ==========================================================================
    # STEP 3: Terms & Privacy
    # ==========================================================================
    
    terms_accepted = Column(Boolean, default=False)
    terms_version = Column(String(20))  # Version of terms accepted
    terms_accepted_at = Column(DateTime(timezone=True))
    
    privacy_accepted = Column(Boolean, default=False)
    privacy_version = Column(String(20))  # Version of privacy policy accepted
    privacy_accepted_at = Column(DateTime(timezone=True))
    
    hipaa_acknowledged = Column(Boolean, default=False)
    hipaa_version = Column(String(20))
    hipaa_acknowledged_at = Column(DateTime(timezone=True))
    
    # ==========================================================================
    # STEP 4: Reminder Preferences
    # ==========================================================================
    
    reminder_preference_set = Column(Boolean, default=False)
    reminder_channel = Column(String(20))  # email, sms, both
    reminder_email = Column(String(255))  # May be different from account email
    reminder_phone = Column(String(20))   # May be different from account phone
    reminder_time = Column(String(10))    # e.g., "09:00"
    reminder_timezone = Column(String(50))
    reminder_preference_at = Column(DateTime(timezone=True))
    
    # ==========================================================================
    # COMPLETION STATUS
    # ==========================================================================
    
    is_fully_onboarded = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime(timezone=True))
    first_login_at = Column(DateTime(timezone=True))
    
    # ==========================================================================
    # NOTIFICATIONS SENT
    # ==========================================================================
    
    welcome_email_sent = Column(Boolean, default=False)
    welcome_email_sent_at = Column(DateTime(timezone=True))
    welcome_sms_sent = Column(Boolean, default=False)
    welcome_sms_sent_at = Column(DateTime(timezone=True))
    
    # Reminder emails/SMS about completing onboarding
    reminder_count = Column(Integer, default=0)
    last_reminder_sent_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationship
    referral = relationship("PatientReferral", back_populates="onboarding_status")


# =============================================================================
# NOTIFICATION LOG
# =============================================================================

class OnboardingNotificationLog(Base):
    """
    Logs all notifications sent during onboarding.
    
    Used for:
    - Audit trail
    - Debugging delivery issues
    - Retry logic
    """
    __tablename__ = "onboarding_notification_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_uuid = Column(UUID(as_uuid=True), index=True)
    referral_uuid = Column(UUID(as_uuid=True), index=True)
    
    # Notification details
    notification_type = Column(String(50))  # welcome, reminder, password_reset
    channel = Column(String(20))  # email, sms
    recipient = Column(String(255))  # email address or phone number
    
    # Status
    status = Column(String(20))  # sent, delivered, failed, bounced
    status_message = Column(Text)
    
    # AWS service info
    aws_message_id = Column(String(100))  # SES/SNS message ID
    
    # Content (for debugging)
    subject = Column(String(500))
    body_preview = Column(String(500))  # First 500 chars
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))

