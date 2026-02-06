"""
AEGIS API Main Application

FastAPI application with REST endpoints and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import json

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
import os

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from aegis.config import get_settings

# Configure structured logging with PHI redaction
def phi_redaction_processor(logger, method_name, event_dict):
    """Redact PHI from log messages."""
    try:
        from aegis.security.phi_detection import redact_phi
        
        # Redact PHI from message field
        if "event" in event_dict:
            event_dict["event"] = redact_phi(str(event_dict["event"]))
        
        # Redact PHI from all string values
        for key, value in event_dict.items():
            if isinstance(value, str) and key not in ["level", "logger", "timestamp"]:
                event_dict[key] = redact_phi(value)
    except Exception:
        pass  # If PHI detection fails, log anyway
    
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        phi_redaction_processor,  # Add PHI redaction
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
    from aegis.db import init_db_clients, close_db_clients
    
    settings = get_settings()
    
    # Startup
    logger.info(
        "Starting AEGIS API",
        env=settings.app.env,
        debug=settings.app.debug,
        llm_provider=settings.llm.llm_provider,
    )
    
    # Initialize all database connections
    try:
        db_clients = await init_db_clients(settings)
        app.state.db = db_clients
        logger.info(
            "Database connections ready",
            postgres=db_clients.postgres is not None,
            graph=db_clients.graph is not None,
            opensearch=db_clients.opensearch is not None,
            redis=db_clients.redis is not None,
        )
    except Exception as e:
        logger.error("Failed to initialize databases", error=str(e))
        # Continue anyway - mock clients will be used
    
    yield
    
    # Shutdown
    logger.info("Shutting down AEGIS API")
    await close_db_clients()


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
async def health_check(request: Request):
    """
    Comprehensive health check endpoint for load balancers and monitoring.
    
    Checks all services and reports status. In production (MOCK_MODE=false),
    returns 503 if any critical service is down.
    """
    settings = get_settings()
    mock_mode = settings.app.mock_mode
    
    services = {"api": "up"}
    service_details = {}
    
    # Check PostgreSQL
    if hasattr(request.app.state, "db") and request.app.state.db:
        db = request.app.state.db
        # Check if it's a mock instance
        postgres_type = type(db.postgres).__name__ if db.postgres else None
        if postgres_type and "Mock" in postgres_type:
            services["postgres"] = "mock"
            service_details["postgres"] = {"type": "mock"}
        elif db.postgres:
            try:
                # Test actual connection
                async with db.postgres.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                services["postgres"] = "up"
                service_details["postgres"] = {"type": "real", "status": "connected"}
            except Exception as e:
                services["postgres"] = "down"
                service_details["postgres"] = {"type": "real", "error": str(e)}
        else:
            services["postgres"] = "down"
            service_details["postgres"] = {"type": "none"}
    else:
        services["postgres"] = "not_initialized"
        service_details["postgres"] = {"type": "not_initialized"}
    
    # Check Graph DB
    try:
        from aegis.graph.client import get_graph_client
        graph = await get_graph_client()
        if hasattr(graph, 'is_mock') and graph.is_mock:
            services["graph_db"] = "mock"
            service_details["graph_db"] = {"type": "mock"}
        elif hasattr(graph, 'health_check'):
            if await graph.health_check():
                services["graph_db"] = "up"
                service_details["graph_db"] = {"type": "real", "status": "connected"}
            else:
                services["graph_db"] = "down"
                service_details["graph_db"] = {"type": "real", "status": "unhealthy"}
        else:
            services["graph_db"] = "up"  # Assume up if no health_check method
            service_details["graph_db"] = {"type": "real", "status": "assumed_up"}
    except Exception as e:
        services["graph_db"] = "down"
        service_details["graph_db"] = {"type": "error", "error": str(e)}
    
    # Check OpenSearch
    if hasattr(request.app.state, "db") and request.app.state.db:
        db = request.app.state.db
        opensearch_type = type(db.opensearch).__name__ if db.opensearch else None
        if opensearch_type and "Mock" in opensearch_type:
            services["opensearch"] = "mock"
            service_details["opensearch"] = {"type": "mock"}
        elif db.opensearch:
            try:
                info = await db.opensearch.info()
                services["opensearch"] = "up"
                service_details["opensearch"] = {"type": "real", "version": info.get("version", {}).get("number")}
            except Exception as e:
                services["opensearch"] = "down"
                service_details["opensearch"] = {"type": "real", "error": str(e)}
        else:
            services["opensearch"] = "down"
            service_details["opensearch"] = {"type": "none"}
    else:
        services["opensearch"] = "not_initialized"
        service_details["opensearch"] = {"type": "not_initialized"}
    
    # Check Redis
    if hasattr(request.app.state, "db") and request.app.state.db:
        db = request.app.state.db
        redis_type = type(db.redis).__name__ if db.redis else None
        if redis_type and "Mock" in redis_type:
            services["redis"] = "mock"
            service_details["redis"] = {"type": "mock"}
        elif db.redis:
            try:
                await db.redis.ping()
                services["redis"] = "up"
                service_details["redis"] = {"type": "real", "status": "connected"}
            except Exception as e:
                services["redis"] = "down"
                service_details["redis"] = {"type": "real", "error": str(e)}
        else:
            services["redis"] = "down"
            service_details["redis"] = {"type": "none"}
    else:
        services["redis"] = "not_initialized"
        service_details["redis"] = {"type": "not_initialized"}
    
    # Check DynamoDB
    if hasattr(request.app.state, "db") and request.app.state.db:
        db = request.app.state.db
        if db.dynamodb and hasattr(db.dynamodb, 'is_mock') and db.dynamodb.is_mock:
            services["dynamodb"] = "mock"
            service_details["dynamodb"] = {"type": "mock"}
        elif db.dynamodb:
            services["dynamodb"] = "up"
            service_details["dynamodb"] = {"type": "real"}
        else:
            services["dynamodb"] = "down"
            service_details["dynamodb"] = {"type": "none"}
    else:
        services["dynamodb"] = "not_initialized"
        service_details["dynamodb"] = {"type": "not_initialized"}
    
    # Determine overall status
    critical_services = ["postgres", "graph_db"]
    critical_down = [s for s in critical_services if services.get(s) == "down"]
    mock_services = [s for s in services.keys() if services.get(s) == "mock"]
    
    # In production (MOCK_MODE=false), fail if critical services are down
    if not mock_mode and critical_down:
        status_code = 503
        overall_status = "unhealthy"
    elif mock_services:
        status_code = 200
        overall_status = "degraded" if critical_down else "healthy"
    else:
        status_code = 200
        overall_status = "healthy" if not critical_down else "degraded"
    
    response = {
        "status": overall_status,
        "env": settings.app.env,
        "mock_mode": mock_mode,
        "services": services,
        "service_details": service_details,
        "mock_services": mock_services,
        "critical_services_down": critical_down,
    }
    
        return JSONResponse(
            content=response,
            status_code=status_code
        )


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
from aegis.api.routes.denials import router as denials_router
from aegis.api.routes.workflows import router as workflows_router
from aegis.api.routes.orchestrator import router as orchestrator_router
from aegis.api.routes.observability import router as observability_router
from aegis.api.routes.integrations import router as integrations_router
from aegis.api.routes.llm import router as llm_router
from aegis.api.routes.rag import router as rag_router
from aegis.api.routes.security import router as security_router
from aegis.api.routes.ml import router as ml_router
from aegis.integrations.cds_hooks import router as cds_hooks_router
from aegis.integrations.epic_smart import router as epic_smart_router
from aegis.events.kafka_consumer import router as events_router
from aegis.clinical.sdoh import router as sdoh_router
from aegis.clinical.symptoms import router as symptoms_router
from aegis.notifications.webhooks import router as notifications_router

# Bridge Apps
try:
    from aegis.bridge_apps.oncolife import oncolife_router
    app.include_router(oncolife_router, prefix="/v1")
except (ImportError, AttributeError) as e:
    logger.warning(f"Oncolife bridge app not available: {e}")

# V1 API routes
app.include_router(auth_router, prefix="/v1")
app.include_router(ingestion_router, prefix="/v1")
app.include_router(patients_router, prefix="/v1")
app.include_router(claims_router, prefix="/v1")
app.include_router(agents_router, prefix="/v1")
app.include_router(denials_router, prefix="/v1")
app.include_router(workflows_router, prefix="/v1")
app.include_router(orchestrator_router, prefix="/v1")
app.include_router(observability_router, prefix="/v1")
app.include_router(integrations_router, prefix="/v1")
app.include_router(llm_router, prefix="/v1")
app.include_router(rag_router, prefix="/v1")
app.include_router(security_router, prefix="/v1")
app.include_router(ml_router, prefix="/v1")
app.include_router(cds_hooks_router)  # CDS Hooks at root level per spec
app.include_router(epic_smart_router, prefix="/v1")
app.include_router(events_router, prefix="/v1")
app.include_router(sdoh_router, prefix="/v1")
app.include_router(symptoms_router, prefix="/v1")
app.include_router(notifications_router, prefix="/v1")

# GraphQL prototype mount (strawberry)
from aegis.api.routes.graphql import graphql_app
app.mount("/v1/graphql", graphql_app)


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
