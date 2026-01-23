"""
Base Graph Provider

Abstract base class defining the interface for all graph database providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseGraphProvider(ABC):
    """
    Abstract base class for graph database providers.
    
    All graph implementations (JanusGraph, Neptune, Neo4j) must implement this interface.
    This ensures the application code remains database-agnostic.
    """
    
    def __init__(self, connection_url: str, **kwargs):
        self.connection_url = connection_url
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the graph database."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the graph database connection."""
        pass
    
    async def __aenter__(self) -> "BaseGraphProvider":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
    
    # ==================== VERTEX OPERATIONS ====================
    
    @abstractmethod
    async def create_vertex(
        self, 
        label: str, 
        properties: dict[str, Any],
        tenant_id: str = "default"
    ) -> str:
        """
        Create a vertex in the graph.
        
        Args:
            label: Vertex label (e.g., 'Patient', 'Encounter')
            properties: Vertex properties
            tenant_id: Multi-tenant isolation ID
            
        Returns:
            Vertex ID
        """
        pass
    
    @abstractmethod
    async def get_vertex(self, vertex_id: str) -> dict[str, Any] | None:
        """
        Get a vertex by ID.
        
        Args:
            vertex_id: The vertex ID
            
        Returns:
            Vertex properties or None if not found
        """
        pass
    
    @abstractmethod
    async def update_vertex(
        self, 
        vertex_id: str, 
        properties: dict[str, Any]
    ) -> bool:
        """
        Update vertex properties.
        
        Args:
            vertex_id: The vertex ID
            properties: Properties to update
            
        Returns:
            True if updated, False if vertex not found
        """
        pass
    
    @abstractmethod
    async def delete_vertex(self, vertex_id: str) -> bool:
        """
        Delete a vertex and its edges.
        
        Args:
            vertex_id: The vertex ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def find_vertices(
        self,
        label: str,
        filters: dict[str, Any] | None = None,
        tenant_id: str = "default",
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Find vertices by label and optional filters.
        
        Args:
            label: Vertex label
            filters: Property filters (exact match)
            tenant_id: Multi-tenant isolation
            limit: Maximum results
            
        Returns:
            List of vertex dictionaries
        """
        pass
    
    # ==================== EDGE OPERATIONS ====================
    
    @abstractmethod
    async def create_edge(
        self,
        from_vertex_id: str,
        to_vertex_id: str,
        label: str,
        properties: dict[str, Any] | None = None
    ) -> str:
        """
        Create an edge between two vertices.
        
        Args:
            from_vertex_id: Source vertex ID
            to_vertex_id: Target vertex ID
            label: Edge label (e.g., 'HAS_ENCOUNTER', 'TREATED_BY')
            properties: Edge properties
            
        Returns:
            Edge ID
        """
        pass
    
    @abstractmethod
    async def get_edges(
        self,
        vertex_id: str,
        direction: str = "both",  # 'in', 'out', 'both'
        edge_label: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get edges connected to a vertex.
        
        Args:
            vertex_id: The vertex ID
            direction: Edge direction
            edge_label: Filter by edge label
            
        Returns:
            List of edge dictionaries
        """
        pass
    
    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge by ID."""
        pass
    
    # ==================== TRAVERSAL OPERATIONS ====================
    
    @abstractmethod
    async def traverse(
        self,
        start_vertex_id: str,
        path_pattern: list[str],
        max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """
        Traverse the graph following a pattern.
        
        Args:
            start_vertex_id: Starting vertex
            path_pattern: Edge labels to follow (e.g., ['HAS_ENCOUNTER', 'HAS_DIAGNOSIS'])
            max_depth: Maximum traversal depth
            
        Returns:
            List of reached vertices
        """
        pass
    
    @abstractmethod
    async def execute_query(
        self, 
        query: str, 
        bindings: dict[str, Any] | None = None
    ) -> list[Any]:
        """
        Execute a raw query (Gremlin/Cypher depending on backend).
        
        Args:
            query: Query string
            bindings: Parameter bindings
            
        Returns:
            Query results
        """
        pass
    
    # ==================== HEALTH & ADMIN ====================
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the database is healthy."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        pass
