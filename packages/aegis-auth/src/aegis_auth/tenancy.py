"""
Multi-Tenancy Service

Schema-per-tenant isolation for healthcare SaaS.
Each tenant (health system, clinic) has isolated data.
"""

from contextvars import ContextVar
from typing import Any
from uuid import uuid4
import structlog

from aegis_auth.models import Tenant, User

logger = structlog.get_logger(__name__)

# Context variable for current tenant (thread-safe)
_current_tenant: ContextVar[Tenant | None] = ContextVar("current_tenant", default=None)
_current_user: ContextVar[User | None] = ContextVar("current_user", default=None)


class TenantContext:
    """
    Tenant context manager for request-scoped isolation.
    
    Usage:
        async with TenantContext(tenant, user):
            # All operations scoped to this tenant
            patients = await get_patients()
    """
    
    def __init__(self, tenant: Tenant, user: User | None = None):
        self.tenant = tenant
        self.user = user
        self._tenant_token = None
        self._user_token = None
    
    def __enter__(self):
        self._tenant_token = _current_tenant.set(self.tenant)
        if self.user:
            self._user_token = _current_user.set(self.user)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _current_tenant.reset(self._tenant_token)
        if self._user_token:
            _current_user.reset(self._user_token)
        return False
    
    async def __aenter__(self):
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def get_current_tenant() -> Tenant | None:
    """Get the current tenant from context."""
    return _current_tenant.get()


def get_current_user() -> User | None:
    """Get the current user from context."""
    return _current_user.get()


def require_tenant() -> Tenant:
    """Get current tenant or raise error."""
    tenant = get_current_tenant()
    if tenant is None:
        raise TenantError("No tenant context - use TenantContext")
    return tenant


def require_user() -> User:
    """Get current user or raise error."""
    user = get_current_user()
    if user is None:
        raise TenantError("No user context")
    return user


class TenantError(Exception):
    """Tenant-related error."""
    pass


class TenantService:
    """
    Service for managing tenants.
    
    Handles tenant CRUD, configuration, and schema management.
    """
    
    def __init__(self, storage: Any = None):
        self._storage = storage or InMemoryTenantStorage()
    
    async def create_tenant(
        self,
        name: str,
        slug: str,
        tenant_type: str = "provider",
        config: dict | None = None
    ) -> Tenant:
        """Create a new tenant."""
        # Validate slug uniqueness
        existing = await self._storage.get_by_slug(slug)
        if existing:
            raise TenantError(f"Tenant slug already exists: {slug}")
        
        tenant = Tenant(
            id=str(uuid4()),
            name=name,
            slug=slug,
            type=tenant_type,
            config=config or {},
        )
        
        await self._storage.save(tenant)
        
        # Initialize tenant schema/namespace
        await self._initialize_tenant_schema(tenant)
        
        logger.info("Created tenant", tenant_id=tenant.id, name=name)
        return tenant
    
    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get tenant by ID."""
        return await self._storage.get(tenant_id)
    
    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by URL slug."""
        return await self._storage.get_by_slug(slug)
    
    async def update_tenant(
        self,
        tenant_id: str,
        updates: dict
    ) -> Tenant | None:
        """Update tenant configuration."""
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        await self._storage.save(tenant)
        return tenant
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete tenant (soft delete - deactivate)."""
        tenant = await self._storage.get(tenant_id)
        if not tenant:
            return False
        
        tenant.is_active = False
        await self._storage.save(tenant)
        
        logger.warning("Deactivated tenant", tenant_id=tenant_id)
        return True
    
    async def list_tenants(
        self,
        active_only: bool = True
    ) -> list[Tenant]:
        """List all tenants."""
        return await self._storage.list(active_only=active_only)
    
    async def _initialize_tenant_schema(self, tenant: Tenant) -> None:
        """
        Initialize isolated schema/namespace for tenant.
        
        For graph DB: Create tenant-prefixed vertex labels
        For relational: Create tenant schema or use RLS
        """
        # This will be implemented based on storage backend
        logger.info("Initialized schema for tenant", tenant_id=tenant.id)


class InMemoryTenantStorage:
    """In-memory tenant storage for development."""
    
    def __init__(self):
        self._tenants: dict[str, Tenant] = {}
        self._by_slug: dict[str, str] = {}
    
    async def save(self, tenant: Tenant) -> None:
        self._tenants[tenant.id] = tenant
        self._by_slug[tenant.slug] = tenant.id
    
    async def get(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)
    
    async def get_by_slug(self, slug: str) -> Tenant | None:
        tenant_id = self._by_slug.get(slug)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None
    
    async def list(self, active_only: bool = True) -> list[Tenant]:
        tenants = list(self._tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.is_active]
        return tenants


def get_tenant_schema_prefix(tenant: Tenant | None = None) -> str:
    """
    Get schema prefix for tenant-isolated queries.
    
    Used to prefix vertex labels, table names, etc.
    """
    t = tenant or get_current_tenant()
    if t is None:
        return "default"
    return f"t_{t.slug}"


def tenant_vertex_label(base_label: str, tenant: Tenant | None = None) -> str:
    """Get tenant-scoped vertex label for graph queries."""
    prefix = get_tenant_schema_prefix(tenant)
    return f"{prefix}_{base_label}"
