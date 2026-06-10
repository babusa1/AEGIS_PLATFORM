"""
API Version 1 - Doctor API
==========================

This package contains the v1 API endpoints.

Endpoints:
- /health: Health check
- /auth: Authentication (login, logout, password management)
- /clinics: Clinic management
- /staff: Staff and physician management
- /patients: Patient data access (read-only)

Usage:
    from api.v1 import api_router
    
    app.include_router(api_router, prefix="/api/v1")
"""

from .router import api_router

__all__ = ["api_router"]





