# ADR-007: API Versioning Strategy

## Status
Accepted

## Context
AEGIS API will evolve over time. We need a versioning strategy that allows introducing breaking changes without disrupting existing clients.

## Decision
**URL path versioning with semantic version policy**

### Versioning Format

```
/v1/patients/{id}       # Version 1
/v2/patients/{id}       # Version 2 (future)
```

### Why URL Path Versioning?

| Method | Pros | Cons |
|--------|------|------|
| URL path (`/v1/`) | Explicit, easy to route, cacheable | Clutters URL |
| Header (`Accept-Version: 1`) | Clean URLs | Hidden, hard to test |
| Query param (`?version=1`) | Easy to add | Not RESTful |

**Decision**: URL path versioning for explicitness and simplicity.

### Version Lifecycle

```
v1 (current)    →  Stable, production
v2 (next)       →  Beta, new features
v1-deprecated   →  Sunset in 6 months
```

### Deprecation Policy

1. **Announce**: 6 months notice before deprecation
2. **Deprecation header**: `Deprecation: true` header on deprecated endpoints
3. **Sunset header**: `Sunset: Sat, 01 Jan 2028 00:00:00 GMT`
4. **Migration guide**: Documentation for upgrading

### API Structure

```
/v1/
├── auth/
│   ├── POST /token          # Login
│   └── POST /refresh        # Refresh token
├── patients/
│   ├── GET /                # List patients
│   ├── POST /               # Create patient
│   ├── GET /{id}            # Get patient
│   ├── GET /{id}/360        # Patient 360 view
│   └── GET /{id}/timeline   # Patient timeline
├── claims/
│   ├── GET /                # List claims
│   └── GET /{id}            # Get claim
├── rcm/
│   ├── GET /denials         # List denials
│   ├── POST /appeals        # Create appeal
│   └── GET /analytics       # RCM analytics
├── quality/
│   ├── GET /measures        # Quality measures
│   └── GET /care-gaps       # Care gaps
├── agents/
│   ├── POST /invoke         # Invoke agent
│   └── GET /sessions/{id}   # Get session
└── admin/
    ├── tenants/             # Tenant management
    └── users/               # User management
```

### Breaking vs Non-Breaking Changes

**Non-breaking (no version bump)**:
- Adding new endpoints
- Adding optional fields to responses
- Adding optional query parameters
- Performance improvements

**Breaking (requires new version)**:
- Removing endpoints
- Removing or renaming fields
- Changing field types
- Changing authentication

### Implementation

```python
# FastAPI versioned routers
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")
v2_router = APIRouter(prefix="/v2")

# Include in app
app.include_router(v1_router)
app.include_router(v2_router)

# Deprecation middleware
@v1_router.get("/old-endpoint", deprecated=True)
async def old_endpoint():
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Jan 2028 00:00:00 GMT"
    ...
```

## Consequences
- Clear versioning visible in URLs
- Multiple versions can coexist
- Deprecation process gives clients time to migrate
- OpenAPI spec generated per version

## References
- [API Versioning Best Practices](https://www.postman.com/api-platform/api-versioning/)
- [RFC 8594: Sunset Header](https://datatracker.ietf.org/doc/html/rfc8594)
