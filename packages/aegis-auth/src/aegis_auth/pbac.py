"""
Purpose-Based Access Control (PBAC)

HIPAA-compliant access control based on:
- Who: User identity and roles
- What: Resource being accessed
- Why: Purpose/reason for access

This goes beyond RBAC by requiring a legitimate purpose for PHI access.
"""

from dataclasses import dataclass
from typing import Callable, Any
import structlog

from aegis_auth.models import (
    User, UserRole, AccessContext, AccessPurpose, AuditEntry
)

logger = structlog.get_logger(__name__)


@dataclass
class PBACPolicy:
    """
    Policy rule for PBAC authorization.
    
    Example:
        # Physicians can access patient data for treatment
        PBACPolicy(
            roles=[UserRole.PHYSICIAN],
            resource_types=["Patient", "Encounter", "Observation"],
            purposes=[AccessPurpose.TREATMENT],
            actions=["read", "write"],
        )
    """
    
    roles: list[UserRole]
    resource_types: list[str]
    purposes: list[AccessPurpose]
    actions: list[str]
    
    # Optional conditions
    require_patient_relationship: bool = False
    require_same_tenant: bool = True
    require_mfa: bool = False
    
    # Custom condition function
    custom_condition: Callable[[AccessContext], bool] | None = None
    
    def matches(self, context: AccessContext) -> bool:
        """Check if this policy matches the access context."""
        # Check role
        user_roles = context.user.tenant_roles.get(context.tenant_id, [])
        if not any(role in user_roles for role in self.roles):
            return False
        
        # Check resource type
        if context.resource_type not in self.resource_types:
            return False
        
        # Check purpose
        if context.purpose not in self.purposes:
            return False
        
        # Check action
        if context.action not in self.actions:
            return False
        
        # Check tenant
        if self.require_same_tenant:
            if context.user.tenant_id != context.tenant_id:
                return False
        
        # Check MFA
        if self.require_mfa:
            if not context.user.mfa_enabled:
                return False
        
        # Custom condition
        if self.custom_condition:
            if not self.custom_condition(context):
                return False
        
        return True


# ==================== DEFAULT POLICIES ====================

DEFAULT_POLICIES = [
    # Admins - full access for operations
    PBACPolicy(
        roles=[UserRole.ADMIN],
        resource_types=["*"],
        purposes=[AccessPurpose.OPERATIONS],
        actions=["read", "write", "delete", "execute"],
    ),
    
    # Physicians - treatment access to clinical data
    PBACPolicy(
        roles=[UserRole.PHYSICIAN],
        resource_types=[
            "Patient", "Encounter", "Diagnosis", "Procedure",
            "Observation", "Medication", "AllergyIntolerance",
            "CarePlan", "Goal", "CareTeam"
        ],
        purposes=[AccessPurpose.TREATMENT],
        actions=["read", "write"],
    ),
    
    # Nurses - treatment access (read-heavy)
    PBACPolicy(
        roles=[UserRole.NURSE],
        resource_types=[
            "Patient", "Encounter", "Diagnosis",
            "Observation", "Medication", "AllergyIntolerance",
            "Task", "Communication"
        ],
        purposes=[AccessPurpose.TREATMENT],
        actions=["read", "write"],
    ),
    
    # Care Managers - care coordination
    PBACPolicy(
        roles=[UserRole.CARE_MANAGER],
        resource_types=[
            "Patient", "Encounter", "CarePlan", "Goal",
            "CareTeam", "Task", "Referral", "Communication",
            "RiskScore", "CareGap", "SDOHAssessment"
        ],
        purposes=[AccessPurpose.TREATMENT, AccessPurpose.OPERATIONS],
        actions=["read", "write"],
    ),
    
    # Billing - payment/claims access
    PBACPolicy(
        roles=[UserRole.BILLING],
        resource_types=[
            "Patient", "Encounter", "Claim", "ClaimLine",
            "Denial", "Authorization", "Coverage"
        ],
        purposes=[AccessPurpose.PAYMENT],
        actions=["read", "write"],
    ),
    
    # Analysts - read-only for operations
    PBACPolicy(
        roles=[UserRole.ANALYST],
        resource_types=[
            "Patient", "Encounter", "Diagnosis", "Procedure",
            "Observation", "Claim", "RiskScore", "CareGap",
            "CohortMembership", "QualityMeasure"
        ],
        purposes=[AccessPurpose.OPERATIONS, AccessPurpose.RESEARCH],
        actions=["read"],
    ),
    
    # Emergency access (break-glass)
    PBACPolicy(
        roles=[UserRole.PHYSICIAN, UserRole.NURSE],
        resource_types=["*"],
        purposes=[AccessPurpose.EMERGENCY],
        actions=["read"],
        require_mfa=True,  # Extra security for break-glass
    ),
    
    # Patient access to own data
    PBACPolicy(
        roles=[UserRole.PATIENT],
        resource_types=[
            "Patient", "Encounter", "Diagnosis", "Procedure",
            "Observation", "Medication", "AllergyIntolerance",
            "Appointment", "Communication", "DocumentReference"
        ],
        purposes=[AccessPurpose.PATIENT_REQUEST],
        actions=["read"],
        # Custom: can only access own data
        custom_condition=lambda ctx: ctx.patient_id == ctx.user.id,
    ),
]


class PBACEngine:
    """
    PBAC authorization engine.
    
    Evaluates access requests against policies and logs decisions.
    """
    
    def __init__(self, policies: list[PBACPolicy] | None = None):
        self.policies = policies or DEFAULT_POLICIES.copy()
        self._audit_handler: Callable[[AuditEntry], None] | None = None
    
    def add_policy(self, policy: PBACPolicy) -> None:
        """Add a custom policy."""
        self.policies.append(policy)
    
    def set_audit_handler(self, handler: Callable[[AuditEntry], None]) -> None:
        """Set handler for audit entries."""
        self._audit_handler = handler
    
    def check_access(self, context: AccessContext) -> tuple[bool, str | None]:
        """
        Check if access should be granted.
        
        Args:
            context: Access context with user, resource, purpose
            
        Returns:
            Tuple of (allowed, denial_reason)
        """
        # Check each policy
        for policy in self.policies:
            if policy.matches(context):
                self._log_access(context, allowed=True)
                return True, None
        
        # No matching policy - deny
        denial_reason = (
            f"No policy allows {context.user.email} with role(s) "
            f"{context.user.tenant_roles.get(context.tenant_id, [])} "
            f"to {context.action} {context.resource_type} "
            f"for purpose {context.purpose.value}"
        )
        
        self._log_access(context, allowed=False, reason=denial_reason)
        
        return False, denial_reason
    
    def _log_access(
        self,
        context: AccessContext,
        allowed: bool,
        reason: str | None = None
    ) -> None:
        """Log access attempt to audit trail."""
        entry = AuditEntry(
            event_type="access" if allowed else "denied",
            user_id=context.user.id,
            user_email=context.user.email,
            user_roles=[r.value for r in context.user.tenant_roles.get(context.tenant_id, [])],
            tenant_id=context.tenant_id,
            resource_type=context.resource_type,
            resource_id=context.resource_id,
            patient_id=context.patient_id,
            purpose=context.purpose,
            purpose_detail=context.purpose_detail,
            success=allowed,
            denial_reason=reason,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            request_id=context.request_id,
            timestamp=context.timestamp,
        )
        
        if self._audit_handler:
            self._audit_handler(entry)
        
        # Also log via structlog
        if allowed:
            logger.info(
                "Access granted",
                user=context.user.email,
                resource=context.resource_type,
                purpose=context.purpose.value,
            )
        else:
            logger.warning(
                "Access denied",
                user=context.user.email,
                resource=context.resource_type,
                purpose=context.purpose.value,
                reason=reason,
            )


# ==================== MODULE-LEVEL HELPERS ====================

_engine: PBACEngine | None = None


def get_pbac_engine() -> PBACEngine:
    """Get the global PBAC engine."""
    global _engine
    if _engine is None:
        _engine = PBACEngine()
    return _engine


def check_access(context: AccessContext) -> tuple[bool, str | None]:
    """
    Check access using global engine.
    
    Convenience function for common use case.
    """
    return get_pbac_engine().check_access(context)


def require_access(context: AccessContext) -> None:
    """
    Require access or raise exception.
    
    Use in route handlers:
        require_access(AccessContext(user=user, resource_type="Patient", ...))
    """
    from aegis_auth.providers.base import AuthorizationError
    
    allowed, reason = check_access(context)
    if not allowed:
        raise AuthorizationError(reason)
