"""
Domain-Specific Database Models for OncoLife Patient API.

This module organizes SQLAlchemy models by domain:
- user.py: User authentication and profile models
- patient.py: Patient-specific models
- conversation.py: Chat, messages, and symptom tracking
- medical.py: Medical records, chemo, and clinical data
- referral.py: Patient referrals, onboarding, and notifications
- onboarding_schema.py: Normalized schema for fax/OCR onboarding
- education.py: Patient education resources and delivery

All models inherit from Base and use appropriate mixins.

Usage:
    from db.models import Patient, Conversation, Message
    from db.models import User, PatientProfile
    from db.models import PatientReferral, PatientOnboardingStatus
    from db.models import Provider, OncologyProfile, Medication
    from db.models import Symptom, EducationDocument, PatientSummary
"""

from .user import User, PatientProfile, StaffProfile
from .patient import Patient
from .conversation import Conversation, Message
from .medical import (
    ChemoSession,
    ChemoSymptom,
    DiaryEntry,
    ConversationSummary,
)
from .referral import (
    PatientReferral,
    PatientOnboardingStatus,
    ReferralDocument,
    OnboardingNotificationLog,
    ReferralStatus,
    OnboardingStep,
    NotificationChannel,
)
from .onboarding_schema import (
    Provider,
    OncologyProfile,
    Medication,
    FaxIngestionLog,
    OcrFieldConfidence,
    MedicationCategory,
    OcrFieldStatus,
    FaxProcessingStatus,
    OCR_CONFIDENCE_THRESHOLDS,
    get_confidence_threshold,
    is_field_acceptable,
)
from .education import (
    Symptom,
    SymptomSession,
    RuleEvaluation,
    EducationDocument,
    Disclaimer,
    CareTeamHandout,
    PatientSummary,
    MedicationTried,
    EducationDeliveryLog,
    EducationAccessLog,
    SymptomCategory,
    SessionStatus,
    TriageSeverity,
    DocumentStatus,
    MedicationEffectiveness,
    get_default_disclaimer,
    get_symptom_catalog,
)

__all__ = [
    # User models
    "User",
    "PatientProfile",
    "StaffProfile",
    # Patient models
    "Patient",
    # Conversation models
    "Conversation",
    "Message",
    # Medical models
    "ChemoSession",
    "ChemoSymptom",
    "DiaryEntry",
    "ConversationSummary",
    # Referral/Onboarding models
    "PatientReferral",
    "PatientOnboardingStatus",
    "ReferralDocument",
    "OnboardingNotificationLog",
    "ReferralStatus",
    "OnboardingStep",
    "NotificationChannel",
    # Normalized Onboarding Schema
    "Provider",
    "OncologyProfile",
    "Medication",
    "FaxIngestionLog",
    "OcrFieldConfidence",
    "MedicationCategory",
    "OcrFieldStatus",
    "FaxProcessingStatus",
    "OCR_CONFIDENCE_THRESHOLDS",
    "get_confidence_threshold",
    "is_field_acceptable",
    # Education Module
    "Symptom",
    "SymptomSession",
    "RuleEvaluation",
    "EducationDocument",
    "Disclaimer",
    "CareTeamHandout",
    "PatientSummary",
    "MedicationTried",
    "EducationDeliveryLog",
    "EducationAccessLog",
    "SymptomCategory",
    "SessionStatus",
    "TriageSeverity",
    "DocumentStatus",
    "MedicationEffectiveness",
    "get_default_disclaimer",
    "get_symptom_catalog",
]

