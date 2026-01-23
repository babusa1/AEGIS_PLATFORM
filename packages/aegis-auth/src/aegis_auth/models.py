"""
Auth Domain Models

Core models for authentication, authorization, and multi-tenancy.
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Standard healthcare roles."""
    ADMIN = "admin"
    PHYSICIAN = "physician"
    NURSE = "nurse"
    CARE_MANAGER = "care_manager"
    BILLING = "billing"
    ANALYST = "analyst"
    PATIENT = "patient"
    SYSTEM = "system"


class AccessPurpose(str, Enum):
    """
    HIPAA-aligned access purposes for PBAC.
    
    These map to legitimate reasons for accessing PHI.
    """
    TREATMENT = "treatment"           # Direct patient care
    PAYMENT = "payment"               # Billing, claims
    OPERATIONS = "operations"         # Quality, compliance
    RESEARCH = "research"             # IRB-approved research
    PUBLIC_HEALTH = "public_health"   # Reporting requirements
    EMERGENCY = "emergency"           # Break-glass access
    PATIENT_REQUEST = "patient_request"  # Patient-initiated


class Tenant(BaseModel):
    """
    Tenant (organization) in multi-tenant system.
    
    Each tenant has isolated data and configuration.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="URL-safe identifier")
    
    # Type
    type: Literal["provider", "payer", "vendor", "research"] = "provider"
    
    # Status
    is_active: bool = True
    
    # Configuration
    config: dict | None = Field(default=None, description="Tenant-specific config")
    
    # Compliance
    hipaa_baa_signed: bool = False
    data_region: str = Field(default="us-east-1", description="Data residency")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class User(BaseModel):
    """
    Authenticated user.
    
    Users belong to one or more tenants with specific roles.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Identity (from OIDC provider)
    sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="Email address")
    email_verified: bool = False
    
    # Profile
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    
    # Tenant membership
    tenant_id: str = Field(..., description="Primary tenant")
    tenant_roles: dict[str, list[UserRole]] = Field(
        default_factory=dict,
        description="Roles per tenant: {tenant_id: [roles]}"
    )
    
    # Healthcare-specific
    npi: str | None = Field(default=None, description="NPI if provider")
    credentials: str | None = Field(default=None, description="MD, RN, etc.")
    
    # Status
    is_active: bool = True
    
    # MFA
    mfa_enabled: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    
    def has_role(self, role: UserRole, tenant_id: str | None = None) -> bool:
        """Check if user has a specific role."""
        tid = tenant_id or self.tenant_id
        roles = self.tenant_roles.get(tid, [])
        return role in roles
    
    def is_admin(self, tenant_id: str | None = None) -> bool:
        """Check if user is admin for tenant."""
        return self.has_role(UserRole.ADMIN, tenant_id)


class AccessContext(BaseModel):
    """
    Context for an access request.
    
    Used by PBAC to make authorization decisions.
    """
    
    # Who
    user: User
    
    # What
    resource_type: str = Field(..., description="Resource being accessed")
    resource_id: str | None = Field(default=None, description="Specific resource ID")
    action: Literal["read", "write", "delete", "execute"] = "read"
    
    # Why (HIPAA purpose)
    purpose: AccessPurpose = Field(..., description="Reason for access")
    purpose_detail: str | None = Field(default=None, description="Additional context")
    
    # Where
    tenant_id: str = Field(..., description="Tenant context")
    
    # Patient context (if applicable)
    patient_id: str | None = Field(default=None, description="Patient being accessed")
    
    # Request metadata
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditEntry(BaseModel):
    """
    Audit log entry for PHI access.
    
    HIPAA requires logging all access to protected health information.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # What happened
    event_type: Literal[
        "login", "logout", "access", "modify", "delete",
        "export", "print", "break_glass", "denied"
    ] = Field(..., description="Event type")
    
    # Who
    user_id: str = Field(..., description="User who performed action")
    user_email: str | None = None
    user_roles: list[str] | None = None
    
    # Context
    tenant_id: str = Field(..., description="Tenant context")
    
    # Resource
    resource_type: str | None = None
    resource_id: str | None = None
    patient_id: str | None = Field(default=None, description="Patient if PHI access")
    
    # Purpose
    purpose: AccessPurpose | None = None
    purpose_detail: str | None = None
    
    # Outcome
    success: bool = True
    denial_reason: str | None = None
    
    # Request
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int | None = None
    
    # Additional data
    metadata: dict | None = None
