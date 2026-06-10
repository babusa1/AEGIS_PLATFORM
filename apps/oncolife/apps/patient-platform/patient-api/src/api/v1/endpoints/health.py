"""
Health Check Endpoints.

Provides endpoints for:
- Basic health check (for load balancers)
- Readiness check (dependencies ready - with DB verification)
- Liveness check (application alive)
- Detailed health info

These endpoints are used by orchestrators (AWS ECS, Kubernetes)
and load balancers (AWS ALB) to determine application health.

Response Codes:
- 200: Healthy / Ready
- 503: Unhealthy / Not Ready (dependencies down)
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any
import time

from core import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", summary="Basic health check")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns a simple status indicating the API is running.
    Used by load balancers and monitoring systems.
    
    This is a lightweight check that doesn't verify dependencies.
    Use /health/ready for a comprehensive check.
    
    Returns:
        {"status": "ok"}
    """
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check with DB verification")
async def readiness_check() -> JSONResponse:
    """
    Readiness check for dependent services.
    
    Checks if all dependencies (databases, external services)
    are available and the application is ready to serve traffic.
    
    This endpoint verifies:
    - Patient database connectivity
    - Response latency
    
    Returns:
        - 200 with health status if all checks pass
        - 503 if any critical dependency is unavailable
    """
    from db.session import check_patient_db_health
    
    start_time = time.perf_counter()
    checks = {}
    is_healthy = True
    
    # Check Patient Database
    try:
        db_health = check_patient_db_health()
        checks["patient_database"] = db_health
        if db_health.get("status") != "ok":
            is_healthy = False
    except Exception as e:
        logger.error(f"Patient DB health check exception: {e}")
        checks["patient_database"] = {"status": "error", "error": str(e)}
        is_healthy = False
    
    # Calculate total check time
    total_time_ms = (time.perf_counter() - start_time) * 1000
    
    response_data = {
        "status": "ready" if is_healthy else "not_ready",
        "checks": checks,
        "total_check_time_ms": round(total_time_ms, 2),
    }
    
    if is_healthy:
        return JSONResponse(status_code=200, content=response_data)
    else:
        logger.warning(
            "Readiness check failed",
            extra={"checks": checks}
        )
        return JSONResponse(status_code=503, content=response_data)


@router.get("/health/live", summary="Liveness check")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for application health.
    
    Indicates if the application process is alive and responsive.
    Used by orchestrators to determine if the container needs restart.
    
    This is a lightweight check that only verifies the process is running.
    
    Returns:
        {"status": "alive"}
    """
    return {"status": "alive"}


@router.get("/health/info", summary="Application info")
async def app_info() -> Dict[str, Any]:
    """
    Get application information.
    
    Returns version and environment info for debugging.
    Note: Don't expose sensitive configuration here.
    
    Returns:
        Application metadata
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/detailed", summary="Detailed health check")
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check with all system information.
    
    Provides comprehensive health status including:
    - All database connections
    - Memory usage
    - Uptime
    
    Note: This endpoint may be slower due to comprehensive checks.
    Use /health for quick load balancer checks.
    
    Returns:
        Detailed health information
    """
    import os
    import psutil
    from db.session import check_patient_db_health
    
    start_time = time.perf_counter()
    checks = {}
    warnings = []
    
    # Database checks
    try:
        checks["patient_database"] = check_patient_db_health()
    except Exception as e:
        checks["patient_database"] = {"status": "error", "error": str(e)}
    
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
    is_healthy = all(
        check.get("status") == "ok" 
        for check in checks.values()
    )
    
    total_time_ms = (time.perf_counter() - start_time) * 1000
    
    response_data = {
        "status": "healthy" if is_healthy else "degraded",
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "checks": checks,
        "warnings": warnings if warnings else None,
        "total_check_time_ms": round(total_time_ms, 2),
    }
    
    status_code = 200 if is_healthy else 503
    return JSONResponse(status_code=status_code, content=response_data)



