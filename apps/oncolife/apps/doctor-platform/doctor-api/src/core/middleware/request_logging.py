"""
Request Logging Middleware - Doctor API
=======================================

This middleware logs all incoming requests and outgoing responses.
Provides structured logging for monitoring and debugging.

Logged information:
- Request: method, path, query params, client IP, user agent
- Response: status code, response time
- Excludes: health check endpoints, sensitive data

Usage:
    Applied automatically via setup_middleware()
"""

import time
from typing import Set
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import get_logger

logger = get_logger(__name__)

# Paths to exclude from logging (health checks, metrics, etc.)
EXCLUDED_PATHS: Set[str] = {
    "/health",
    "/health/",
    "/api/v1/health",
    "/api/v1/health/",
    "/metrics",
    "/metrics/",
    "/favicon.ico",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    
    Provides structured logging for all API calls, useful for:
    - Debugging issues
    - Performance monitoring
    - Audit trails
    - Security analysis
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Log the request and response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response
        """
        # Skip logging for excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)
        
        # Start timing
        start_time = time.perf_counter()
        
        # Extract request information
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown")[:100],
        }
        
        # Log incoming request
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"request": request_info}
        )
        
        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log the error
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request": request_info,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }
            )
            raise
        
        # Calculate response time
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logger.error
        elif response.status_code >= 400:
            log_level = logger.warning
        else:
            log_level = logger.info
        
        # Log the response
        log_level(
            f"Response: {request.method} {request.url.path} -> {response.status_code}",
            extra={
                "request": request_info,
                "response": {
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            }
        )
        
        # Add timing header to response
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract the client IP address from the request.
        
        Handles proxy headers (X-Forwarded-For) for deployments
        behind load balancers.
        
        Args:
            request: The HTTP request
            
        Returns:
            The client IP address
        """
        # Check for forwarded header (when behind a proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"





