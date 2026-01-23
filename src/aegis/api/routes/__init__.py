"""
AEGIS API Routes

All API route modules.
"""

from aegis.api.routes.auth import router as auth_router
from aegis.api.routes.ingestion import router as ingestion_router
from aegis.api.routes.patients import router as patients_router
from aegis.api.routes.claims import router as claims_router
from aegis.api.routes.agents import router as agents_router

__all__ = [
    "auth_router",
    "ingestion_router",
    "patients_router",
    "claims_router",
    "agents_router",
]
