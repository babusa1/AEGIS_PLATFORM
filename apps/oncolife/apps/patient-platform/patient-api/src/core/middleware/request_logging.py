"""
Request Logging Middleware for OncoLife Patient API.

This middleware logs:
- All incoming HTTP requests
- Response status codes
- Request duration
- Client information

Provides visibility into API usage patterns and helps identify:
- Slow endpoints
- Error patterns
- Usage statistics

Note: Sensitive data (passwords, tokens) should NOT be logged.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    
    Logs the following for each request:
    - HTTP method and path
    - Response status code
    - Request duration in milliseconds
    - Client IP address
    - User agent (truncated)
    
    Excludes:
    - Health check endpoints (to reduce log noise)
    - Static file requests
    """
    
    # Endpoints to exclude from logging (reduce noise)
    EXCLUDED_PATHS = {
        "/health",
        "/healthz",
        "/ready",
        "/metrics",
        "/favicon.ico",
    }
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Log request and response details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response
        """
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = self._get_user_agent(request)
        
        # Log incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_query": str(request.query_params) if request.query_params else None,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )
        
        # Process the request
        response: Response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Log response
        log_level = self._get_log_level(response.status_code)
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            }
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Handles forwarded requests (behind proxy/load balancer).
        
        Args:
            request: HTTP request
        
        Returns:
            Client IP address string
        """
        # Check for forwarded header (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # First IP in the list is the original client
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header (Nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_user_agent(self, request: Request) -> str:
        """
        Get truncated user agent string.
        
        Truncates long user agents to prevent log bloat.
        
        Args:
            request: HTTP request
        
        Returns:
            User agent string (max 100 chars)
        """
        user_agent = request.headers.get("User-Agent", "unknown")
        # Truncate long user agents
        if len(user_agent) > 100:
            return user_agent[:97] + "..."
        return user_agent
    
    def _get_log_level(self, status_code: int) -> int:
        """
        Determine log level based on response status code.
        
        Args:
            status_code: HTTP response status code
        
        Returns:
            Logging level constant
        """
        import logging
        
        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        else:
            return logging.INFO





