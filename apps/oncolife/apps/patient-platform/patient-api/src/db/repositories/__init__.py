"""
Repository Layer for Database Operations.

This module provides the repository pattern for data access:
- Abstracts database operations from business logic
- Provides a clean interface for CRUD operations
- Enables easier testing through dependency injection
- Centralizes query logic

Architecture:
    repositories/
    ├── base.py              # Generic CRUD repository
    ├── patient_repository.py
    ├── conversation_repository.py
    ├── chemo_repository.py
    ├── diary_repository.py
    ├── summary_repository.py
    └── profile_repository.py

Usage:
    from db.repositories import PatientRepository, ChemoRepository
    
    class PatientService:
        def __init__(self, patient_repo: PatientRepository):
            self.patient_repo = patient_repo
        
        def get_patient(self, patient_id: UUID) -> Patient:
            return self.patient_repo.get_by_id(patient_id)
"""

from .base import BaseRepository
from .patient_repository import PatientRepository
from .conversation_repository import ConversationRepository
from .chemo_repository import ChemoRepository
from .diary_repository import DiaryRepository
from .summary_repository import SummaryRepository
from .profile_repository import ProfileRepository

__all__ = [
    "BaseRepository",
    "PatientRepository",
    "ConversationRepository",
    "ChemoRepository",
    "DiaryRepository",
    "SummaryRepository",
    "ProfileRepository",
]

