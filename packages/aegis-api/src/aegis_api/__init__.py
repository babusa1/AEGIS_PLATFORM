"""
AEGIS API

FastAPI application with Purpose-Based Access Control (PBAC).
"""

from aegis_api.app import create_app
from aegis_api.security.pbac import PBACMiddleware, Purpose

__version__ = "0.1.0"

__all__ = ["create_app", "PBACMiddleware", "Purpose"]
