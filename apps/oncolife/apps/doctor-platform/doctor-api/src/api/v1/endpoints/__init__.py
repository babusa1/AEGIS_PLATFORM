"""
API V1 Endpoints - Doctor API
=============================

This package contains all v1 API endpoint modules.

Modules:
- health: Health check and status endpoints
- auth: Authentication and authorization
- clinics: Clinic management
- staff: Staff and physician management
- patients: Patient data access

Each module contains a FastAPI router with related endpoints.
"""

from . import health
from . import auth
from . import clinics
from . import staff
from . import patients

__all__ = [
    "health",
    "auth",
    "clinics",
    "staff",
    "patients",
]





