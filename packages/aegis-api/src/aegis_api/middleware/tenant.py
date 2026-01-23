"""
Multi-Tenant Middleware
"""

import structlog

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extract and validate tenant context.
    
    Requires X-Tenant-ID header on API requests.
    """
    
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip exempt paths
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # Get tenant from header
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id:
            # Development default
            tenant_id = "dev-tenant"
        
        # Validate tenant (in production, check against tenant registry)
        # For now, just set it
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response
