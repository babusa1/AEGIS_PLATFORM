"""
Middleware Package - Doctor API
===============================

This package contains FastAPI middleware components for:
- Request/response logging
- Correlation ID tracking
- Global error handling
- Rate limiting

Usage:
    from core.middleware import setup_middleware
    
    app = FastAPI()
    setup_middleware(app)
"""

from fastapi import FastAPI

from .correlation_id import CorrelationIdMiddleware
from .request_logging import RequestLoggingMiddleware
from .error_handler import setup_exception_handlers
from .rate_limiting import setup_rate_limiting, limiter


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application.
    
    Middleware is applied in reverse order (last added = first executed).
    
    Order of execution for requests:
    1. CorrelationIdMiddleware (add/extract correlation ID)
    2. RequestLoggingMiddleware (log request/response)
    3. Rate limiting check
    4. Route handlers
    
    Args:
        app: The FastAPI application instance
    """
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Setup rate limiting (must be before other middleware)
    setup_rate_limiting(app)
    
    # Add middleware (order matters - last added is executed first)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)


__all__ = [
    "setup_middleware",
    "CorrelationIdMiddleware",
    "RequestLoggingMiddleware",
    "setup_exception_handlers",
    "limiter",
]





