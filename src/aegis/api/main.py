"""
AEGIS API Main Application

FastAPI application with REST endpoints and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
import os

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from aegis.config import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    settings = get_settings()
    
    # Startup
    logger.info(
        "Starting AEGIS API",
        env=settings.app.env,
        debug=settings.app.debug,
        llm_provider=settings.llm.llm_provider,
    )
    
    # Initialize connections (will be implemented)
    # await initialize_graph_db()
    # await initialize_opensearch()
    # await initialize_kafka()
    
    yield
    
    # Shutdown
    logger.info("Shutting down AEGIS API")
    # await close_connections()


# Create FastAPI application
app = FastAPI(
    title="AEGIS API",
    description="The Agentic Operating System for Healthcare",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AEGIS API",
        "version": "0.1.0",
        "description": "The Agentic Operating System for Healthcare",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    settings = get_settings()
    return {
        "status": "healthy",
        "env": settings.app.env,
        "services": {
            "api": "up",
            "graph_db": "pending",  # Will be implemented
            "opensearch": "pending",
            "kafka": "pending",
        },
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - returns 200 when all dependencies are ready."""
    # TODO: Check actual service connections
    return {"status": "ready"}


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check - returns 200 if the service is alive."""
    return {"status": "alive"}


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if get_settings().app.debug else None,
        },
    )


# =============================================================================
# Include Routers
# =============================================================================

from aegis.api.routes.auth import router as auth_router
from aegis.api.routes.ingestion import router as ingestion_router
from aegis.api.routes.patients import router as patients_router
from aegis.api.routes.claims import router as claims_router
from aegis.api.routes.agents import router as agents_router

# V1 API routes
app.include_router(auth_router, prefix="/v1")
app.include_router(ingestion_router, prefix="/v1")
app.include_router(patients_router, prefix="/v1")
app.include_router(claims_router, prefix="/v1")
app.include_router(agents_router, prefix="/v1")


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "aegis.api.main:app",
        host=settings.app.api_host,
        port=settings.app.api_port,
        reload=settings.app.api_reload,
        workers=settings.app.api_workers,
    )
