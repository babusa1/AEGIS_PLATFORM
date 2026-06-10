"""
================================================================================
OncoLife Doctor API - Main Application Entry Point
================================================================================

Module:         main.py
Description:    FastAPI application entry point for the OncoLife Doctor Platform.
                Provides APIs for healthcare staff to manage patients, view 
                symptom timelines, alerts, weekly reports, and coordinate care.

Created:        2025-12-15
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Application Structure:
    - core/: Configuration, logging, exceptions, middleware
    - db/: Database models, repositories, session management
    - services/: Business logic layer (dashboard, patient, staff services)
    - api/v1/: Versioned REST API endpoints

Key Features:
    - Dashboard with severity-ranked patient list
    - Patient symptom timeline visualization
    - Weekly reports generation
    - Staff management (nurses, MAs, navigators)
    - Cross-database queries to patient platform

Usage:
    # Development
    uvicorn main:app --reload --port 8001
    
    # Production
    uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core imports
from core.config import settings
from core.logging import setup_logging, get_logger
from core.middleware import setup_middleware

# API imports
from api.v1.router import api_router

# Setup logging first
setup_logging()
logger = get_logger(__name__)


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    
    Startup:
    - Log application start
    - Verify database connections
    
    Shutdown:
    - Log application shutdown
    - Cleanup resources
    """
    # Startup
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version} "
        f"in {settings.environment} mode"
    )
    
    # Verify database connections
    try:
        from db.session import verify_database_connections
        db_status = verify_database_connections()
        logger.info(f"Database connection status: {db_status}")
    except Exception as e:
        logger.warning(f"Database verification failed: {e}")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# =============================================================================
# Application Factory
# =============================================================================

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This factory function:
    1. Creates the FastAPI instance with metadata
    2. Configures CORS middleware
    3. Sets up custom middleware (logging, error handling)
    4. Mounts API routers
    
    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI application
    app = FastAPI(
        title=settings.app_name,
        description="""
        ## OncoLife Doctor API
        
        Backend API for the doctor/staff portal, enabling healthcare 
        providers to manage patients, view alerts, and coordinate care.
        
        ### Features
        - **Authentication**: AWS Cognito integration
        - **Clinic Management**: Create and manage healthcare facilities
        - **Staff Management**: Manage physicians and staff members
        - **Patient Access**: View patient data and symptom alerts
        
        ### Authentication
        All endpoints (except /health) require a valid JWT token.
        Include the token in the Authorization header:
        ```
        Authorization: Bearer <your_token>
        ```
        """,
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup custom middleware (logging, error handling, correlation ID)
    setup_middleware(app)
    
    # Mount versioned API routers
    app.include_router(
        api_router,
        prefix="/api/v1",
    )
    
    # =========================================================================
    # LEGACY ROUTES - REMOVED
    # =========================================================================
    # 
    # All legacy routes have been migrated to /api/v1/
    # 
    # Migration complete:
    # - /auth/*  -> /api/v1/auth/*
    # - /staff/* -> /api/v1/staff/*
    #
    
    return app


# =============================================================================
# Application Instance
# =============================================================================

# Create the application instance
app = create_application()


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information.
    
    Returns basic information about the API.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.is_development else "Disabled in production",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Basic health check endpoint.
    
    Returns simple status for load balancer and container health checks.
    For detailed health info, use /api/v1/health/ready
    
    This endpoint is required by:
    - Docker HEALTHCHECK
    - AWS ALB Target Group health checks
    - Kubernetes liveness probes
    """
    return {"status": "ok"}


# =============================================================================
# Development Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )

