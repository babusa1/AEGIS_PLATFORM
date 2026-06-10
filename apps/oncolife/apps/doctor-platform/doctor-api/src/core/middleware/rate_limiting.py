"""
Rate Limiting Middleware for OncoLife Doctor API.

This module provides API rate limiting to:
- Prevent abuse and DDoS attacks
- Ensure fair usage across clients
- Protect authentication endpoints from brute force

Rate limits are configurable per endpoint type:
- Auth endpoints: Stricter limits (prevent brute force)
- API endpoints: Moderate limits for dashboard usage
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger
from core import settings

logger = get_logger(__name__)


# =============================================================================
# RATE LIMIT KEY FUNCTIONS
# =============================================================================

def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client making the request.
    
    Uses the following priority:
    1. Authenticated staff ID (from JWT token)
    2. X-Forwarded-For header (behind proxy/load balancer)
    3. X-Real-IP header (Nginx)
    4. Direct client IP
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"staff:{user_id}"
    
    # Fall back to IP-based identification
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return f"ip:{real_ip}"
    
    if request.client:
        return f"ip:{request.client.host}"
    
    return "ip:unknown"


# =============================================================================
# LIMITER CONFIGURATION
# =============================================================================

limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["100/minute", "500/hour"],  # Default limits
    headers_enabled=True,
    strategy="fixed-window",
)


# =============================================================================
# RATE LIMIT CONSTANTS
# =============================================================================

AUTH_RATE_LIMIT = "5/minute"
PASSWORD_RESET_LIMIT = "3/minute"
API_RATE_LIMIT = "60/minute"
DASHBOARD_RATE_LIMIT = "120/minute"  # Higher for dashboard polling


# =============================================================================
# CUSTOM RATE LIMIT EXCEEDED HANDLER
# =============================================================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    client_id = get_client_identifier(request)
    
    logger.warning(
        f"Rate limit exceeded for client",
        extra={
            "client_id": client_id,
            "path": request.url.path,
            "method": request.method,
            "limit": str(exc.detail),
        }
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please slow down and try again later.",
            "details": {
                "limit": str(exc.detail),
                "retry_after": "60 seconds",
            }
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": str(exc.detail),
        }
    )


# =============================================================================
# SETUP FUNCTION
# =============================================================================

def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting for the FastAPI application.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info(
        "Rate limiting configured",
        extra={
            "default_limits": limiter._default_limits,
            "strategy": "fixed-window",
        }
    )


# Decorator shortcuts
auth_limit = limiter.limit(AUTH_RATE_LIMIT)
api_limit = limiter.limit(API_RATE_LIMIT)
dashboard_limit = limiter.limit(DASHBOARD_RATE_LIMIT)


__all__ = [
    "limiter",
    "setup_rate_limiting",
    "get_client_identifier",
    "AUTH_RATE_LIMIT",
    "API_RATE_LIMIT",
    "auth_limit",
    "api_limit",
    "dashboard_limit",
]
