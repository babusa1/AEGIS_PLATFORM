"""
Request/Response Logging Middleware
"""

import time
from uuid import uuid4
import structlog

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit trail."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )
        
        response = await call_next(request)
        
        # Log response
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Request completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
