"""
Health Check Endpoints - Doctor API
===================================

Provides health check endpoints for monitoring and load balancers.

Endpoints:
- GET /health: Basic health check (for ALB)
- GET /health/ready: Readiness check with database verification
- GET /health/live: Liveness check
- GET /health/detailed: Comprehensive health information

Response Codes:
- 200: Healthy / Ready
- 503: Unhealthy / Not Ready (dependencies down)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import time

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str
    service: str
    version: str
    timestamp: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="Basic health check endpoint for load balancers and monitoring.",
)
async def health_check():
    """
    Basic health check.
    
    Returns a simple status indicating the service is running.
    This is a lightweight check that does not verify dependencies.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get(
    "/ready",
    summary="Readiness Check with DB Verification",
    description="Detailed readiness check including database connectivity.",
)
async def readiness_check() -> JSONResponse:
    """
    Detailed readiness check with database verification.
    
    Verifies that the service and its dependencies are ready
    to accept traffic. Returns 503 if critical dependencies are unavailable.
    """
    from db.session import check_doctor_db_health, check_patient_db_health
    
    start_time = time.perf_counter()
    checks = {}
    is_healthy = True
    
    # Check doctor database (critical)
    try:
        doctor_health = check_doctor_db_health()
        checks["doctor_database"] = doctor_health
        if doctor_health.get("status") != "ok":
            is_healthy = False
    except Exception as e:
        logger.error(f"Doctor DB health check exception: {e}")
        checks["doctor_database"] = {"status": "error", "error": str(e)}
        is_healthy = False
    
    # Check patient database (optional - for viewing patient data)
    try:
        patient_health = check_patient_db_health()
        checks["patient_database"] = patient_health
        # Patient DB is optional, don't fail if it's not configured
        if patient_health.get("status") == "error":
            logger.warning("Patient database is unavailable")
    except Exception as e:
        logger.error(f"Patient DB health check exception: {e}")
        checks["patient_database"] = {"status": "error", "error": str(e)}
    
    total_time_ms = (time.perf_counter() - start_time) * 1000
    
    # Determine overall status based on doctor DB (critical)
    doctor_ok = checks.get("doctor_database", {}).get("status") == "ok"
    patient_ok = checks.get("patient_database", {}).get("status") == "ok"
    
    if doctor_ok and patient_ok:
        status = "ready"
    elif doctor_ok:
        status = "degraded"  # Doctor DB works but patient DB doesn't
    else:
        status = "not_ready"
    
    response_data = {
        "status": status,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
        "total_check_time_ms": round(total_time_ms, 2),
    }
    
    # Return 503 if not ready (doctor DB is down)
    if status == "not_ready":
        logger.warning("Readiness check failed - doctor database unavailable")
        return JSONResponse(status_code=503, content=response_data)
    
    return JSONResponse(status_code=200, content=response_data)


@router.get("/live", summary="Liveness check")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for container orchestration.
    
    Indicates if the application process is alive and responsive.
    This is a lightweight check - use /ready for dependency checks.
    """
    return {"status": "alive"}


@router.get("/detailed", summary="Detailed health information")
async def detailed_health_check() -> JSONResponse:
    """
    Comprehensive health check with system information.
    
    Includes database status, memory usage, and other metrics.
    This endpoint may be slower due to comprehensive checks.
    """
    import os
    import psutil
    from db.session import check_doctor_db_health, check_patient_db_health
    
    start_time = time.perf_counter()
    checks = {}
    
    # Database checks
    checks["doctor_database"] = check_doctor_db_health()
    checks["patient_database"] = check_patient_db_health()
    
    # System info
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        checks["system"] = {
            "status": "ok",
            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "threads": process.num_threads(),
        }
    except Exception as e:
        checks["system"] = {"status": "error", "error": str(e)}
    
    # Determine overall status
    doctor_ok = checks.get("doctor_database", {}).get("status") == "ok"
    is_healthy = doctor_ok  # Doctor DB is the critical dependency
    
    total_time_ms = (time.perf_counter() - start_time) * 1000
    
    response_data = {
        "status": "healthy" if is_healthy else "degraded",
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_check_time_ms": round(total_time_ms, 2),
    }
    
    status_code = 200 if is_healthy else 503
    return JSONResponse(status_code=status_code, content=response_data)





