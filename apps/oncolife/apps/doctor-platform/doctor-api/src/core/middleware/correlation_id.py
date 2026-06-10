"""
Correlation ID Middleware - Doctor API
======================================

This middleware handles correlation IDs for request tracing:
- Extracts existing correlation ID from request headers
- Generates a new one if not present
- Adds correlation ID to response headers
- Makes correlation ID available for logging

Header: X-Correlation-ID

Usage:
    The correlation ID is automatically set in the logging context
    and can be accessed via:
    
        from core.logging import get_correlation_id
        correlation_id = get_correlation_id()
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import set_correlation_id, get_logger

logger = get_logger(__name__)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for request tracing.
    
    This enables tracking a request through the entire system,
    including across service boundaries.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process the request and add correlation ID.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response with correlation ID header
        """
        # Extract correlation ID from request header or generate a new one
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        
        if not correlation_id:
            # Generate a new correlation ID (short UUID for readability)
            correlation_id = str(uuid.uuid4())[:8]
        
        # Set correlation ID in the logging context
        set_correlation_id(correlation_id)
        
        # Store correlation ID in request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Process the request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        
        return response





