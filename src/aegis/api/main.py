"""
VeritOS API Main Application

FastAPI application with REST endpoints and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import json

import structlog
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

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
        "Starting VeritOS API",
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
    logger.info("Shutting down VeritOS API")
    await close_db_clients()


# Create FastAPI application
app = FastAPI(
    title="VeritOS API",
    description="The Truth Operating System for Healthcare",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
# Note: When allow_credentials=True, cannot use allow_origins=["*"]
# Must specify exact origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],  # Frontend origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Handle OPTIONS preflight requests
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle CORS preflight OPTIONS requests."""
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    headers = {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Max-Age"] = "3600"
    
    return Response(status_code=200, headers=headers)

# Additional CORS handler for all responses (including errors)
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    """Add CORS headers to all responses, including error responses."""
    try:
        response = await call_next(request)
    except Exception as e:
        # If an exception occurs, create a response with CORS headers
        origin = request.headers.get("origin")
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        
        headers = {}
        if origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            headers["Access-Control-Allow-Headers"] = "*"
            headers["Access-Control-Expose-Headers"] = "*"
        
        # Re-raise to let the exception handler deal with it
        # But ensure CORS headers are added
        raise
    
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
    
    return response


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "VeritOS API",
        "version": "0.1.0",
        "description": "The Truth Operating System for Healthcare",
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler with CORS headers."""
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    headers = dict(exc.headers) if exc.headers else {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Expose-Headers"] = "*"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors with CORS headers."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    
    # Add CORS headers to error response
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    headers = {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Expose-Headers"] = "*"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if get_settings().app.debug else None,
        },
        headers=headers,
    )


# =============================================================================
# Include Routers
# =============================================================================

# Helper function to safely include routers
def safe_include_router(module_path: str, router_name: str, prefix: str = None):
    """Safely import and include a router with graceful error handling."""
    try:
        module = __import__(module_path, fromlist=[router_name])
        router = getattr(module, router_name)
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
        return True
    except (ImportError, AttributeError, TypeError) as e:
        logger.debug(f"Router {module_path}.{router_name} not available: {e}")
        return False

# Core routes (required for basic functionality)
safe_include_router("aegis.api.routes.auth", "router", "/v1")

# Optional routes (graceful degradation)
safe_include_router("aegis.api.routes.ingestion", "router", "/v1")
safe_include_router("aegis.api.routes.patients", "router", "/v1")
safe_include_router("aegis.api.routes.claims", "router", "/v1")
safe_include_router("aegis.api.routes.entities", "router", "/v1")
safe_include_router("aegis.api.routes.agents", "router", "/v1")
safe_include_router("aegis.api.routes.denials", "router", "/v1")
safe_include_router("aegis.api.routes.workflows", "router", "/v1")
safe_include_router("aegis.api.routes.orchestrator", "router", "/v1")
safe_include_router("aegis.api.routes.observability", "router", "/v1")
safe_include_router("aegis.api.routes.integrations", "router", "/v1")
safe_include_router("aegis.api.routes.llm", "router", "/v1")
safe_include_router("aegis.api.routes.rag", "router", "/v1")
safe_include_router("aegis.api.routes.security", "router", "/v1")
safe_include_router("aegis.api.routes.ml", "router", "/v1")
safe_include_router("aegis.integrations.cds_hooks", "router", "")  # Root level
safe_include_router("aegis.integrations.epic_smart", "router", "/v1")
safe_include_router("aegis.events.kafka_consumer", "router", "/v1")
safe_include_router("aegis.clinical.sdoh", "router", "/v1")
safe_include_router("aegis.clinical.symptoms", "router", "/v1")
safe_include_router("aegis.notifications.webhooks", "router", "/v1")
safe_include_router("aegis.api.routes.audit", "router", "/v1")
safe_include_router("aegis.api.routes.cowork", "router", "/v1")
safe_include_router("aegis.api.routes.voice", "router", "/v1")

# Bridge Apps
try:
    from aegis.bridge_apps.oncolife import oncolife_router
    if oncolife_router:
        app.include_router(oncolife_router, prefix="/v1")
except (ImportError, AttributeError, TypeError) as e:
    logger.debug(f"Oncolife bridge app not available: {e}")

try:
    from aegis.bridge_apps.chaperone_ckm import ckm_router
    if ckm_router:
        app.include_router(ckm_router, prefix="/v1")
except (ImportError, AttributeError, TypeError, SyntaxError, NameError) as e:
    logger.debug(f"Chaperone CKM bridge app not available: {e}")

# GraphQL prototype mount (strawberry)
try:
    from aegis.api.routes.graphql import graphql_app
    if graphql_app:
        app.mount("/v1/graphql", graphql_app)
except (ImportError, AttributeError, TypeError) as e:
    logger.debug(f"GraphQL app not available: {e}")


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
