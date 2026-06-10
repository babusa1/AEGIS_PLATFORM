"""
Database Models Package - Doctor API
=====================================

This package contains SQLAlchemy ORM models organized by domain:
- clinic: Clinic and location models
- staff: Staff profiles and associations

All models are re-exported here for convenient access.

Usage:
    from db.models import Clinic, StaffProfile, StaffAssociation
"""

from .clinic import Clinic
from .staff import StaffProfile, StaffAssociation

__all__ = [
    # Clinic models
    "Clinic",
    # Staff models
    "StaffProfile",
    "StaffAssociation",
]





