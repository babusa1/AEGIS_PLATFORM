"""Base Repository - Abstract data access pattern"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Base repository pattern for data access.
    
    Abstracts the underlying storage (Graph, Postgres, etc.)
    """
    
    def __init__(self, tenant_id: str, graph_client=None, 
                 postgres_client=None, timeseries_client=None):
        self.tenant_id = tenant_id
        self._graph = graph_client
        self._postgres = postgres_client
        self._timeseries = timeseries_client
    
    @abstractmethod
    async def get(self, id: str) -> T | None:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0, **filters) -> list[T]:
        """List entities with optional filters."""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> str:
        """Create a new entity, return ID."""
        pass
    
    @abstractmethod
    async def update(self, id: str, data: dict) -> bool:
        """Update an entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity."""
        pass
    
    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        return await self.get(id) is not None
    
    def _build_graph_query(self, vertex_label: str, **filters) -> str:
        """Build a Gremlin query with filters."""
        query = f"g.V().hasLabel('{vertex_label}').has('tenant_id', '{self.tenant_id}')"
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, str):
                    query += f".has('{key}', '{value}')"
                else:
                    query += f".has('{key}', {value})"
        return query
    
    def _to_dict(self, entity: T) -> dict:
        """Convert entity to dictionary."""
        if hasattr(entity, "model_dump"):
            return entity.model_dump()
        elif hasattr(entity, "__dict__"):
            return entity.__dict__
        return dict(entity)
