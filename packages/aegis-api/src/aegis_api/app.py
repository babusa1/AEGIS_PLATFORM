"""
FastAPI Application Factory
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from aegis_api.routers import patients, encounters, analytics, ingestion, health
from aegis_api.middleware.logging import LoggingMiddleware
from aegis_api.middleware.tenant import TenantMiddleware

logger = structlog.get_logger(__name__)


def create_app(
    title: str = "AEGIS API",
    debug: bool = False,
) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        title: API title
        debug: Enable debug mode
        
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title=title,
        description="AEGIS - The Agentic Operating System for Healthcare",
        version="0.1.0",
        debug=debug,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TenantMiddleware)
    
    # Routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(patients.router, prefix="/api/v1/patients", tags=["patients"])
    app.include_router(encounters.router, prefix="/api/v1/encounters", tags=["encounters"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(ingestion.router, prefix="/api/v1/ingest", tags=["ingestion"])
    
    @app.on_event("startup")
    async def startup():
        logger.info("AEGIS API starting", version="0.1.0")
    
    @app.on_event("shutdown")
    async def shutdown():
        logger.info("AEGIS API shutting down")
    
    return app


# Default app instance
app = create_app()
