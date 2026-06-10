"""
Correlation ID Middleware for Request Tracing.

This middleware:
- Generates a unique correlation ID for each request
- Accepts existing correlation ID from X-Correlation-ID header
- Adds correlation ID to response headers
- Makes correlation ID available for logging

The correlation ID enables tracing a single request across:
- Multiple log entries
- Microservices
- Async operations
- Error reports

Usage:
    The correlation ID is automatically available in logs:
    
    logger.info("Processing request")
    # Output: {"correlation_id": "abc-123-def", "message": "Processing request", ...}
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import set_correlation_id, get_correlation_id


# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for request tracing.
    
    For each incoming request:
    1. Check for existing X-Correlation-ID header
    2. Generate new UUID if not present
    3. Set correlation ID in context for logging
    4. Add correlation ID to response headers
    
    This enables end-to-end request tracing across services.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and manage correlation ID.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response with correlation ID header
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        
        if not correlation_id:
            # Generate new UUID v4 for this request
            correlation_id = str(uuid.uuid4())
        
        # Set in context for logging
        set_correlation_id(correlation_id)
        
        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Process the request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        
        return response


def get_request_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request state.
    
    Utility function for accessing correlation ID in route handlers.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Correlation ID string
    
    Example:
        @app.get("/patients")
        async def get_patients(request: Request):
            correlation_id = get_request_correlation_id(request)
            logger.info(f"Fetching patients", extra={"correlation_id": correlation_id})
    """
    return getattr(request.state, "correlation_id", None) or get_correlation_id() or "unknown"





