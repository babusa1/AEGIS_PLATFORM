"""
AEGIS Auth Package

Authentication and authorization for healthcare multi-tenant SaaS:
- OIDC provider abstraction (Cognito, Auth0, Okta)
- Purpose-Based Access Control (PBAC) for HIPAA
- Multi-tenant context management
- Audit logging for PHI access
"""

from aegis_auth.provider import AuthProvider, get_auth_provider
from aegis_auth.models import User, Tenant, AccessContext, AuditEntry, AccessPurpose
from aegis_auth.pbac import PBACPolicy, check_access, require_access
from aegis_auth.tenancy import (
    TenantContext,
    TenantService,
    get_current_tenant,
    get_current_user,
    require_tenant,
)
from aegis_auth.audit import AuditService, get_audit_service, audit_access

__version__ = "0.1.0"

__all__ = [
    # Auth
    "AuthProvider",
    "get_auth_provider",
    # Models
    "User",
    "Tenant",
    "AccessContext",
    "AuditEntry",
    "AccessPurpose",
    # PBAC
    "PBACPolicy",
    "check_access",
    "require_access",
    # Tenancy
    "TenantContext",
    "TenantService",
    "get_current_tenant",
    "get_current_user",
    "require_tenant",
    # Audit
    "AuditService",
    "get_audit_service",
    "audit_access",
]
