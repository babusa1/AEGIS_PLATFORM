"""
Service Layer for Business Logic.

This module provides the service layer that:
- Contains all business logic
- Orchestrates operations across repositories
- Handles complex workflows
- Provides a clean interface for API endpoints

Architecture:
    services/
    ├── base.py                  # Base service class
    ├── auth_service.py          # Authentication logic (Cognito)
    ├── patient_service.py       # Patient operations
    ├── chat_service.py          # Symptom checker chat
    ├── chemo_service.py         # Chemotherapy dates
    ├── diary_service.py         # Patient diary entries
    ├── summary_service.py       # Conversation summaries
    ├── profile_service.py       # Patient profile
    ├── ocr_service.py           # AWS Textract OCR with confidence tracking
    ├── notification_service.py  # AWS SES/SNS notifications
    ├── onboarding_service.py    # Patient onboarding orchestration
    ├── fax_service.py           # Fax reception and processing
    ├── medication_categorizer.py # Medication categorization
    └── education_service.py     # Patient education delivery

Principles:
    - Services should be stateless
    - Services orchestrate, repositories persist
    - Services handle business rules and validation
    - Services are easily testable

Usage:
    from services import PatientService, ChatService
    from services import OnboardingService, OCRService
    from services import EducationService
    from services.medication_categorizer import categorize_medication
    
    @app.get("/patients/{patient_id}")
    async def get_patient(
        patient_id: UUID,
        db: Session = Depends(get_patient_db)
    ):
        service = PatientService(db)
        return service.get_patient(patient_id)
"""

from .base import BaseService
from .patient_service import PatientService
from .auth_service import AuthService
from .chat_service import ChatService
from .chemo_service import ChemoService
from .diary_service import DiaryService
from .summary_service import SummaryService
from .profile_service import ProfileService

# Onboarding services
from .ocr_service import OCRService, OCRResult, ExtractedField
from .notification_service import NotificationService
from .onboarding_service import OnboardingService
from .fax_service import FaxService

# Medication categorization
from .medication_categorizer import (
    categorize_medication,
    categorize_medications,
    is_chemotherapy,
    is_supportive,
    is_growth_factor,
    get_neutropenia_risk_medications,
    extract_regimen_medications,
    MedicationCategory,
)

# Education services
from .education_service import EducationService

# Keep backward compatibility
from .conversation_service import ConversationService

__all__ = [
    "BaseService",
    "PatientService",
    "AuthService",
    "ChatService",
    "ChemoService",
    "DiaryService",
    "SummaryService",
    "ProfileService",
    "ConversationService",  # For backward compatibility
    # Onboarding services
    "OCRService",
    "OCRResult",
    "ExtractedField",
    "NotificationService",
    "OnboardingService",
    "FaxService",
    # Medication categorization
    "categorize_medication",
    "categorize_medications",
    "is_chemotherapy",
    "is_supportive",
    "is_growth_factor",
    "get_neutropenia_risk_medications",
    "extract_regimen_medications",
    "MedicationCategory",
    # Education services
    "EducationService",
]

