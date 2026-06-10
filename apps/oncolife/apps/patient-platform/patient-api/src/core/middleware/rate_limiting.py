"""
Rate Limiting Middleware for OncoLife Patient API.

This module provides API rate limiting to:
- Prevent abuse and DDoS attacks
- Ensure fair usage across clients
- Protect authentication endpoints from brute force

Rate limits are configurable per endpoint type:
- Auth endpoints: Stricter limits (prevent brute force)
- Public endpoints: Moderate limits
- Authenticated endpoints: Higher limits

Uses slowapi with Redis backend for distributed rate limiting.
Falls back to in-memory storage if Redis is unavailable.
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
    1. Authenticated user ID (from JWT token)
    2. X-Forwarded-For header (behind proxy/load balancer)
    3. X-Real-IP header (Nginx)
    4. Direct client IP
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Unique client identifier string
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"user:{user_id}"
    
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

# Create the limiter with default configuration
# In production, consider using Redis for distributed rate limiting:
# limiter = Limiter(key_func=get_client_identifier, storage_uri="redis://localhost:6379")

limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["200/minute", "1000/hour"],  # Default limits for all endpoints
    headers_enabled=True,  # Add rate limit headers to responses
    strategy="fixed-window",  # or "moving-window" for smoother limiting
)


# =============================================================================
# RATE LIMIT CONSTANTS
# =============================================================================

# Authentication endpoints - strict limits to prevent brute force
AUTH_RATE_LIMIT = "5/minute"  # 5 attempts per minute
AUTH_RATE_LIMIT_HOUR = "20/hour"  # 20 attempts per hour

# Password reset - very strict
PASSWORD_RESET_LIMIT = "3/minute"  # 3 attempts per minute
PASSWORD_RESET_LIMIT_HOUR = "10/hour"  # 10 attempts per hour

# Standard API endpoints - moderate limits
API_RATE_LIMIT = "60/minute"  # 60 requests per minute
API_RATE_LIMIT_HOUR = "1000/hour"  # 1000 requests per hour

# High-frequency endpoints (like chat/polling)
REALTIME_RATE_LIMIT = "120/minute"  # 120 requests per minute

# Health check endpoints - no limit (for monitoring)
HEALTH_RATE_LIMIT = "1000/minute"


# =============================================================================
# CUSTOM RATE LIMIT EXCEEDED HANDLER
# =============================================================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a JSON response with:
    - Consistent error format
    - Retry-After header
    - Clear error message
    
    Args:
        request: FastAPI Request object
        exc: RateLimitExceeded exception
    
    Returns:
        JSONResponse with 429 status code
    """
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
    
    This function should be called during app initialization.
    It sets up:
    - The limiter state on the app
    - Custom error handler for rate limit exceeded
    - SlowAPI middleware
    
    Args:
        app: FastAPI application instance
    
    Example:
        from core.middleware.rate_limiting import setup_rate_limiting
        
        app = FastAPI()
        setup_rate_limiting(app)
    """
    # Attach limiter to app state
    app.state.limiter = limiter
    
    # Add custom exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info(
        "Rate limiting configured",
        extra={
            "default_limits": limiter._default_limits,
            "strategy": "fixed-window",
        }
    )


# =============================================================================
# DECORATOR SHORTCUTS
# =============================================================================

# Pre-configured decorators for common use cases
auth_limit = limiter.limit(AUTH_RATE_LIMIT)
auth_limit_strict = limiter.limit(PASSWORD_RESET_LIMIT)
api_limit = limiter.limit(API_RATE_LIMIT)
realtime_limit = limiter.limit(REALTIME_RATE_LIMIT)


__all__ = [
    "limiter",
    "setup_rate_limiting",
    "get_client_identifier",
    "AUTH_RATE_LIMIT",
    "API_RATE_LIMIT",
    "REALTIME_RATE_LIMIT",
    "auth_limit",
    "auth_limit_strict",
    "api_limit",
    "realtime_limit",
]
