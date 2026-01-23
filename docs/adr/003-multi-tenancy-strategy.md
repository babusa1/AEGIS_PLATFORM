# ADR-003: Multi-Tenancy Strategy

## Status
Accepted

## Context
AEGIS is a multi-tenant SaaS platform. Each customer (hospital, health system) is a tenant with isolated data. We need to choose an isolation strategy.

## Decision
**Schema-per-tenant in PostgreSQL + Namespace-per-tenant in Graph DB**

### Isolation Strategies Considered

| Strategy | Pros | Cons |
|----------|------|------|
| Shared schema with tenant_id | Simple, cost-effective | Risk of data leaks, noisy neighbor |
| Schema-per-tenant | Strong isolation, easy backup | More schemas to manage |
| Database-per-tenant | Complete isolation | Expensive, complex management |

### Chosen Approach

**PostgreSQL (Metadata/Config)**:
- Schema-per-tenant: `tenant_acme`, `tenant_mercy`, etc.
- Connection pooling with schema switching
- Easy tenant-specific backup/restore

**Graph Database**:
- Namespace prefix on vertices: `acme:Patient:123`, `mercy:Patient:456`
- Query filter: `has('tenant_id', tenant_id)` on all queries
- Enforced at GraphProvider abstraction layer

**Redis Cache**:
- Key prefix: `tenant:acme:cache:...`

**Object Storage (S3)**:
- Bucket prefix: `aegis-data/tenants/acme/...`

### Implementation

```python
class TenantContext:
    tenant_id: str
    tenant_schema: str      # PostgreSQL schema name
    graph_namespace: str    # Graph vertex prefix
    
    @property
    def cache_prefix(self) -> str:
        return f"tenant:{self.tenant_id}:"
    
    @property
    def storage_prefix(self) -> str:
        return f"tenants/{self.tenant_id}/"
```

### Middleware Enforcement

```python
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract tenant from JWT claims
    tenant_id = request.state.user.tenant_id
    
    # Set tenant context for this request
    request.state.tenant = TenantContext(tenant_id=tenant_id)
    
    # All downstream operations use this context
    return await call_next(request)
```

## Consequences
- All queries must include tenant context (enforced by abstraction)
- Cross-tenant queries impossible by design
- Tenant onboarding creates schema + namespace automatically
- Tenant deletion purges all data in isolation

## References
- [Multi-tenant SaaS Patterns](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/overview)
