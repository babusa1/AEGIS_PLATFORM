"""
Purpose-Based Access Control (PBAC)

HIPAA-compliant access control based on declared purpose.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any
from datetime import datetime
import structlog

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class Purpose(str, Enum):
    """Healthcare data access purposes (HIPAA)."""
    TREATMENT = "treatment"
    PAYMENT = "payment"
    OPERATIONS = "operations"
    RESEARCH = "research"
    PUBLIC_HEALTH = "public_health"
    QUALITY = "quality_improvement"
    AUDIT = "audit"
    EMERGENCY = "emergency"


class Action(str, Enum):
    """CRUD actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"


@dataclass
class AccessDecision:
    """Result of PBAC evaluation."""
    allowed: bool
    purpose: Purpose | None
    reason: str
    audit_id: str | None = None


class PBACPolicy:
    """
    Purpose-Based Access Control Policy.
    
    Defines what purposes can access what resources.
    """
    
    # Resource -> Allowed Purposes
    RESOURCE_POLICIES: dict[str, set[Purpose]] = {
        "Patient": {
            Purpose.TREATMENT,
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
            Purpose.EMERGENCY,
        },
        "Encounter": {
            Purpose.TREATMENT,
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
            Purpose.QUALITY,
        },
        "Observation": {
            Purpose.TREATMENT,
            Purpose.RESEARCH,
            Purpose.QUALITY,
        },
        "Claim": {
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
            Purpose.AUDIT,
        },
        "Coverage": {
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
        },
        "GeneticVariant": {
            Purpose.TREATMENT,
            Purpose.RESEARCH,
        },
        "Condition": {
            Purpose.TREATMENT,
            Purpose.RESEARCH,
            Purpose.QUALITY,
        },
        "MedicationRequest": {
            Purpose.TREATMENT,
            Purpose.PAYMENT,
        },
    }
    
    # Role -> Allowed Purposes
    ROLE_PURPOSES: dict[str, set[Purpose]] = {
        "physician": {
            Purpose.TREATMENT,
            Purpose.EMERGENCY,
        },
        "nurse": {
            Purpose.TREATMENT,
        },
        "billing": {
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
        },
        "admin": {
            Purpose.OPERATIONS,
            Purpose.AUDIT,
        },
        "researcher": {
            Purpose.RESEARCH,
            Purpose.QUALITY,
        },
        "system": {
            Purpose.TREATMENT,
            Purpose.PAYMENT,
            Purpose.OPERATIONS,
            Purpose.RESEARCH,
            Purpose.AUDIT,
        },
    }
    
    @classmethod
    def evaluate(
        cls,
        resource: str,
        action: Action,
        purpose: Purpose,
        role: str,
        context: dict | None = None,
    ) -> AccessDecision:
        """
        Evaluate access request.
        
        Args:
            resource: Resource type being accessed
            action: CRUD action
            purpose: Declared purpose for access
            role: User's role
            context: Additional context (emergency, etc.)
            
        Returns:
            AccessDecision
        """
        # Check if role can use this purpose
        allowed_purposes = cls.ROLE_PURPOSES.get(role, set())
        if purpose not in allowed_purposes:
            return AccessDecision(
                allowed=False,
                purpose=purpose,
                reason=f"Role '{role}' cannot access for purpose '{purpose}'",
            )
        
        # Check if purpose allows this resource
        resource_purposes = cls.RESOURCE_POLICIES.get(resource, set())
        if purpose not in resource_purposes:
            return AccessDecision(
                allowed=False,
                purpose=purpose,
                reason=f"Purpose '{purpose}' not allowed for resource '{resource}'",
            )
        
        # Emergency override
        if context and context.get("emergency") and purpose == Purpose.EMERGENCY:
            logger.warning(
                "Emergency access granted",
                resource=resource,
                action=action,
            )
            return AccessDecision(
                allowed=True,
                purpose=purpose,
                reason="Emergency access override",
            )
        
        return AccessDecision(
            allowed=True,
            purpose=purpose,
            reason="Access granted",
        )


class PBACMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for PBAC enforcement.
    
    Requires X-Purpose header on API requests.
    """
    
    # Paths that don't require PBAC
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip exempt paths
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # Get purpose from header
        purpose_header = request.headers.get("X-Purpose")
        
        if not purpose_header:
            # Default to treatment for API calls (can be made stricter)
            request.state.purpose = Purpose.TREATMENT
        else:
            try:
                request.state.purpose = Purpose(purpose_header)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid purpose: {purpose_header}",
                )
        
        response = await call_next(request)
        return response


def require_purpose(*purposes: Purpose):
    """
    Decorator to require specific purposes for an endpoint.
    
    Usage:
        @router.get("/patients/{id}")
        @require_purpose(Purpose.TREATMENT, Purpose.PAYMENT)
        async def get_patient(id: str, request: Request):
            ...
    """
    def decorator(func):
        async def wrapper(*args, request: Request, **kwargs):
            purpose = getattr(request.state, "purpose", None)
            
            if purpose not in purposes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Purpose '{purpose}' not allowed. Required: {[p.value for p in purposes]}",
                )
            
            return await func(*args, request=request, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator
