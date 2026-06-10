"""
Services Package - Doctor API
=============================

This package contains the business logic layer of the application.
Services coordinate between the API endpoints and the data repositories.

Architecture:
- Services handle business rules and validation
- They use repositories for data access
- They can call other services for complex operations

Usage:
    from services import ClinicService, StaffService, AuthService
    
    clinic_service = ClinicService(db)
    clinic = clinic_service.create_clinic(request)
"""

from .base import BaseService
from .clinic_service import ClinicService
from .staff_service import StaffService
from .auth_service import AuthService
from .patient_service import PatientService
from .dashboard_service import DashboardService
from .audit_service import AuditService
from .registration_service import RegistrationService

__all__ = [
    "BaseService",
    "ClinicService",
    "StaffService",
    "AuthService",
    "PatientService",
    "DashboardService",
    "AuditService",
    "RegistrationService",
]

