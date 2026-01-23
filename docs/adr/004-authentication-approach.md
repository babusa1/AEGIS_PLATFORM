# ADR-004: Authentication and Authorization Approach

## Status
Accepted

## Context
AEGIS requires enterprise-grade authentication with support for SSO, MFA, and healthcare-specific access controls (HIPAA compliance).

## Decision
**OIDC-based authentication with Purpose-Based Access Control (PBAC)**

### Authentication: OIDC Provider Abstraction

Support multiple identity providers through abstraction:

```python
class AuthProvider(ABC):
    @abstractmethod
    async def verify_token(self, token: str) -> TokenClaims: ...
    @abstractmethod
    async def get_user_info(self, token: str) -> UserInfo: ...

# Implementations
class CognitoProvider(AuthProvider): ...  # AWS Cognito
class Auth0Provider(AuthProvider): ...    # Auth0
class OIDCProvider(AuthProvider): ...     # Generic OIDC
class LocalProvider(AuthProvider): ...    # Demo/development
```

### Authorization: Purpose-Based Access Control (PBAC)

Beyond traditional RBAC, HIPAA requires tracking the **purpose** of data access:

```python
class AccessPurpose(Enum):
    TREATMENT = "treatment"           # Direct patient care
    PAYMENT = "payment"               # Billing, claims, denials
    OPERATIONS = "operations"         # Quality improvement
    RESEARCH = "research"             # IRB-approved (de-identified)
    PUBLIC_HEALTH = "public_health"   # Reporting requirements

# Every data access specifies purpose
@require_purpose(AccessPurpose.TREATMENT)
async def get_patient_phi(patient_id: str):
    # Access logged with purpose for HIPAA audit
    ...
```

### Role Hierarchy

```python
ROLES = {
    "platform_admin": ["*"],
    "tenant_admin": ["tenant:*", "users:*", "config:*"],
    "physician": ["patients:read", "patients:write", "encounters:*"],
    "nurse": ["patients:read", "encounters:read", "vitals:*"],
    "biller": ["claims:*", "denials:*", "appeals:*"],
    "analyst": ["patients:read", "reports:*", "dashboards:*"],
    "viewer": ["dashboards:view"],
}
```

### Audit Trail

All access logged for HIPAA compliance:

```python
@dataclass
class AuditEntry:
    timestamp: datetime
    user_id: str
    tenant_id: str
    resource: str
    action: str
    purpose: AccessPurpose
    patient_id: str | None
    ip_address: str
    result: Literal["allowed", "denied"]
```

## Consequences
- SSO support for enterprise customers
- MFA enforced for PHI access
- Complete audit trail of all data access
- Purpose tracked for HIPAA "minimum necessary" compliance
- Provider abstraction allows easy switching

## References
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [OpenID Connect](https://openid.net/connect/)
