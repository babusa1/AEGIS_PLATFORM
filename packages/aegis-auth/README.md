# AEGIS Auth

Authentication and authorization for AEGIS Healthcare Platform.

## Features

- **OIDC Provider Abstraction**: Unified interface for Cognito, Auth0, Okta
- **Purpose-Based Access Control (PBAC)**: HIPAA-compliant authorization
- **Multi-tenant Support**: Tenant isolation and user-tenant membership
- **Audit Logging**: PHI access tracking for compliance

## Installation

```bash
pip install aegis-auth

# With AWS Cognito support
pip install aegis-auth[cognito]
```

## Quick Start

### 1. Configure Provider

```python
from aegis_auth import AuthProvider

# AWS Cognito
provider = AuthProvider.create(
    provider_type="cognito",
    issuer_url="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx",
    client_id="your-client-id",
    region="us-east-1"
)

# Auth0
provider = AuthProvider.create(
    provider_type="auth0",
    issuer_url="https://your-tenant.auth0.com",
    client_id="your-client-id",
    client_secret="your-secret",
    audience="https://api.aegis.health"
)
```

### 2. Verify Tokens

```python
await provider.initialize()

# Verify JWT token
claims = await provider.verify_token(token)

# Get user info
user_info = await provider.get_user_info(access_token)
```

### 3. Purpose-Based Access Control

```python
from aegis_auth import check_access, AccessContext, AccessPurpose

# Check if access is allowed
context = AccessContext(
    user=current_user,
    resource_type="Patient",
    resource_id="patient-123",
    action="read",
    purpose=AccessPurpose.TREATMENT,
    tenant_id="hospital-a",
    patient_id="patient-123"
)

allowed, reason = check_access(context)

if not allowed:
    raise PermissionDenied(reason)
```

### 4. Custom Policies

```python
from aegis_auth.pbac import PBACPolicy, get_pbac_engine
from aegis_auth.models import UserRole, AccessPurpose

# Add custom policy
engine = get_pbac_engine()

engine.add_policy(PBACPolicy(
    roles=[UserRole.NURSE],
    resource_types=["Medication"],
    purposes=[AccessPurpose.TREATMENT],
    actions=["read", "write"],
    require_same_tenant=True,
))
```

## HIPAA Access Purposes

| Purpose | Description | Typical Users |
|---------|-------------|---------------|
| `TREATMENT` | Direct patient care | Physicians, nurses |
| `PAYMENT` | Billing, claims | Billing staff |
| `OPERATIONS` | Quality, compliance | Admins, analysts |
| `RESEARCH` | IRB-approved studies | Researchers |
| `EMERGENCY` | Break-glass access | Clinical staff |
| `PATIENT_REQUEST` | Patient-initiated | Patients |

## Audit Logging

All access attempts are logged:

```python
from aegis_auth.pbac import get_pbac_engine

engine = get_pbac_engine()

# Set custom audit handler
def log_to_splunk(entry):
    splunk_client.log(entry.model_dump())

engine.set_audit_handler(log_to_splunk)
```

## FastAPI Integration

```python
from fastapi import Depends, HTTPException
from aegis_auth import get_auth_provider, check_access, AccessContext

async def get_current_user(token: str = Depends(oauth2_scheme)):
    provider = await get_auth_provider()
    claims = await provider.verify_token(token)
    return provider.token_to_user(claims, tenant_id="default")

def require_treatment_access(resource_type: str):
    async def checker(user = Depends(get_current_user)):
        context = AccessContext(
            user=user,
            resource_type=resource_type,
            action="read",
            purpose=AccessPurpose.TREATMENT,
            tenant_id=user.tenant_id
        )
        allowed, reason = check_access(context)
        if not allowed:
            raise HTTPException(403, reason)
        return user
    return checker

@app.get("/patients/{id}")
async def get_patient(
    id: str,
    user = Depends(require_treatment_access("Patient"))
):
    ...
```

## License

MIT
