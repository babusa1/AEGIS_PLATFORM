"""
Middleware Components for OncoLife Patient API.

This module provides FastAPI middleware for:
- Global exception handling
- Request/Response logging
- Correlation ID tracking
- Request timing
- Rate limiting

Usage:
    from core.middleware import setup_middleware
    
    app = FastAPI()
    setup_middleware(app)
"""

from fastapi import FastAPI
from .error_handler import setup_exception_handlers
from .request_logging import RequestLoggingMiddleware
from .correlation_id import CorrelationIdMiddleware
from .rate_limiting import setup_rate_limiting, limiter


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application.
    
    This function should be called after creating the FastAPI app
    but before defining routes.
    
    Middleware is applied in reverse order, so:
    - CorrelationIdMiddleware runs first (sets correlation ID)
    - RequestLoggingMiddleware runs second (logs with correlation ID)
    - Rate limiting is checked
    - Exception handlers catch any errors
    
    Args:
        app: FastAPI application instance
    
    Example:
        from fastapi import FastAPI
        from core.middleware import setup_middleware
        
        app = FastAPI()
        setup_middleware(app)
    """
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Add rate limiting (must be set up before other middleware)
    setup_rate_limiting(app)
    
    # Add middleware (applied in reverse order)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)


__all__ = [
    "setup_middleware",
    "setup_exception_handlers",
    "RequestLoggingMiddleware",
    "CorrelationIdMiddleware",
    "limiter",
]





