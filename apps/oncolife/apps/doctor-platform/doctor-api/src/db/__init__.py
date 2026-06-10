"""
Database Package - Doctor API
=============================

This package provides database infrastructure including:
- Base model classes with common fields
- Session management and dependency injection
- Domain-specific models (clinic, staff)
- Repository pattern for data access

Usage:
    from db import get_doctor_db, get_patient_db
    from db.models import StaffProfile, Clinic
    from db.repositories import StaffRepository, ClinicRepository
"""

from .base import DoctorBase, PatientBase, TimestampMixin
from .session import (
    get_doctor_db,
    get_patient_db,
    doctor_engine,
    patient_engine,
)

__all__ = [
    # Base classes
    "DoctorBase",
    "PatientBase",
    "TimestampMixin",
    # Session management
    "get_doctor_db",
    "get_patient_db",
    "doctor_engine",
    "patient_engine",
]





