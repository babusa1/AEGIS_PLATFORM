"""
API Layer for OncoLife Patient API.

This module provides:
- API versioning structure
- Shared dependencies
- Route organization

Structure:
    api/
    ├── deps.py          # Shared dependencies
    └── v1/              # API version 1
        ├── router.py    # Main v1 router
        ├── endpoints/   # Route handlers
        └── schemas/     # Request/Response models
"""

from .deps import (
    get_current_user,
    get_current_patient,
    get_patient_db,
    get_doctor_db,
)

__all__ = [
    "get_current_user",
    "get_current_patient",
    "get_patient_db",
    "get_doctor_db",
]





