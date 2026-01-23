"""
Health Check Router
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    # TODO: Check database connections
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
