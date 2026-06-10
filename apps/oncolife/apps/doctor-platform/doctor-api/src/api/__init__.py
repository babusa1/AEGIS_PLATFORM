"""
API Package - Doctor API
========================

This package contains the REST API layer organized by version.

Current versions:
- v1: Initial API version (/api/v1/...)

Usage:
    from api.v1 import api_router
    
    app.include_router(api_router, prefix="/api/v1")
"""

from .v1.router import api_router

__all__ = ["api_router"]





