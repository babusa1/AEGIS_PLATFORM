"""
JanusGraph Provider - Real Implementation

Production Gremlin implementation for JanusGraph.
"""

from typing import Any, AsyncIterator
import structlog

from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T, P, Order

from aegis_graph.providers.base import BaseGraphProvider
from aegis_graph.connection import GraphConnectionPool, get_graph_pool
from aegis_graph.schema import SCHEMA

logger = structlog.get_logger(__name__)


class JanusGraphProvider(BaseGraphProvider):
    """
    JanusGraph implementation using Gremlin.
    
    For local development and on-premise deployments.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8182,
        pool_size: int = 10,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self._pool: GraphConnectionPool | None = None
    
    async def initialize(self) -> None:
        """Initialize connection pool."""
        self._pool = await get_graph_pool(
            host=self.host,
            port=self.port,
            pool_size=self.pool_size
        )
        logger.info("JanusGraph provider initialized", host=self.host, port=self.port)
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
    
    async def health_check(self) -> dict:
        """Check JanusGraph health."""
        if not self._pool:
            return {"status": "not_initialized"}
        return await self._pool.health_check()
    
    # ==================== VERTEX OPERATIONS ====================
    
    async def create_vertex(
        self,
        label: str,
        properties: dict[str, Any]
    ) -> str:
        """Create a vertex."""
        async with self._pool.get_traversal() as g:
            query = g.addV(label)
            
            for key, value in properties.items():
                if value is not None:
                    query = query.property(key, value)
            
            result = await query.id().next()
            
            logger.debug("Created vertex", label=label, id=properties.get("id"))
            return str(result)
    
    async def get_vertex(
        self,
        label: str,
        vertex_id: str,
        tenant_id: str | None = None
    ) -> dict | None:
        """Get a vertex by ID."""
        async with self._pool.get_traversal() as g:
            query = g.V().has(label, "id", vertex_id)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            results = await query.valueMap(True).toList()
            
            if results:
                return self._normalize_vertex(results[0])
            return None
    
    async def update_vertex(
        self,
        label: str,
        vertex_id: str,
        properties: dict[str, Any],
        tenant_id: str | None = None
    ) -> bool:
        """Update vertex properties."""
        async with self._pool.get_traversal() as g:
            query = g.V().has(label, "id", vertex_id)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            for key, value in properties.items():
                if key not in ("id", "tenant_id"):
                    query = query.property(key, value)
            
            results = await query.id().toList()
            return len(results) > 0
    
    async def delete_vertex(
        self,
        label: str,
        vertex_id: str,
        tenant_id: str | None = None
    ) -> bool:
        """Delete a vertex."""
        async with self._pool.get_traversal() as g:
            query = g.V().has(label, "id", vertex_id)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            count = await query.drop().iterate()
            return True
    
    async def find_vertices(
        self,
        label: str,
        filters: dict[str, Any],
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """Find vertices by filters."""
        async with self._pool.get_traversal() as g:
            query = g.V().hasLabel(label)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            for key, value in filters.items():
                query = query.has(key, value)
            
            results = await (
                query
                .range(offset, offset + limit)
                .valueMap(True)
                .toList()
            )
            
            return [self._normalize_vertex(v) for v in results]
    
    # ==================== EDGE OPERATIONS ====================
    
    async def create_edge(
        self,
        from_label: str,
        from_id: str,
        edge_label: str,
        to_label: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
        tenant_id: str | None = None
    ) -> str:
        """Create an edge."""
        async with self._pool.get_traversal() as g:
            from_query = g.V().has(from_label, "id", from_id)
            to_query = __.V().has(to_label, "id", to_id)
            
            if tenant_id:
                from_query = from_query.has("tenant_id", tenant_id)
                to_query = to_query.has("tenant_id", tenant_id)
            
            query = from_query.addE(edge_label).to(to_query)
            
            if properties:
                for key, value in properties.items():
                    if value is not None:
                        query = query.property(key, value)
            
            result = await query.id().next()
            return str(result)
    
    async def get_edges(
        self,
        from_label: str,
        from_id: str,
        edge_label: str | None = None,
        direction: str = "out",
        tenant_id: str | None = None
    ) -> list[dict]:
        """Get edges from a vertex."""
        async with self._pool.get_traversal() as g:
            query = g.V().has(from_label, "id", from_id)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            if direction == "out":
                edge_query = query.outE(edge_label) if edge_label else query.outE()
            elif direction == "in":
                edge_query = query.inE(edge_label) if edge_label else query.inE()
            else:
                edge_query = query.bothE(edge_label) if edge_label else query.bothE()
            
            results = await (
                edge_query
                .project("edge", "target")
                .by(__.valueMap(True))
                .by(__.inV().valueMap(True) if direction == "out" else __.outV().valueMap(True))
                .toList()
            )
            
            return results
    
    # ==================== TRAVERSAL OPERATIONS ====================
    
    async def traverse(
        self,
        start_label: str,
        start_id: str,
        path: list[str],
        tenant_id: str | None = None
    ) -> list[dict]:
        """Traverse the graph following a path of edge labels."""
        async with self._pool.get_traversal() as g:
            query = g.V().has(start_label, "id", start_id)
            
            if tenant_id:
                query = query.has("tenant_id", tenant_id)
            
            for edge_label in path:
                query = query.out(edge_label)
            
            results = await query.valueMap(True).toList()
            return [self._normalize_vertex(v) for v in results]
    
    async def execute_query(
        self,
        query_string: str,
        bindings: dict[str, Any] | None = None
    ) -> list[Any]:
        """Execute a raw Gremlin query string."""
        async with self._pool.get_connection() as conn:
            result = await conn.submit(query_string, bindings or {})
            return await result.all().result()
    
    # ==================== HELPERS ====================
    
    def _normalize_vertex(self, vertex_map: dict) -> dict:
        """Normalize JanusGraph vertex map to simple dict."""
        result = {}
        for key, value in vertex_map.items():
            if key == T.id:
                result["_graph_id"] = value
            elif key == T.label:
                result["_label"] = value
            elif isinstance(value, list) and len(value) == 1:
                result[key] = value[0]
            else:
                result[key] = value
        return result
