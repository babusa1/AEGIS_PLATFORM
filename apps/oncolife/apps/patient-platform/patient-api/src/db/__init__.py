"""
Database Module for OncoLife Patient API.

This module provides:
- Database session management
- Base model classes with common functionality
- Domain-specific models (patient, conversation, medical)
- Repository pattern for data access

Architecture:
    db/
    ├── base.py          # Base model class with common fields
    ├── session.py       # Session management and dependencies
    ├── models/          # Domain-specific SQLAlchemy models
    │   ├── user.py
    │   ├── patient.py
    │   ├── conversation.py
    │   └── medical.py
    └── repositories/    # Data access layer
        ├── base.py
        ├── patient_repository.py
        └── conversation_repository.py

Usage:
    from db import get_patient_db, Base
    from db.models import Patient, Conversation
    from db.repositories import PatientRepository
"""

from .base import Base, TimestampMixin, UUIDMixin
from .session import (
    get_patient_db,
    get_doctor_db,
    PatientSessionLocal,
    DoctorSessionLocal,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # Session management
    "get_patient_db",
    "get_doctor_db",
    "PatientSessionLocal",
    "DoctorSessionLocal",
]
