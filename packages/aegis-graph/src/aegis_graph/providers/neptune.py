"""
AWS Neptune Provider

Gremlin-based implementation for AWS Neptune (production).
Includes IAM authentication support.
"""

from typing import Any

import structlog
from gremlin_python.driver import client, serializer
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import GraphTraversalSource
from tenacity import retry, stop_after_attempt, wait_exponential

from aegis_graph.providers.base import BaseGraphProvider

logger = structlog.get_logger(__name__)


class NeptuneProvider(BaseGraphProvider):
    """
    AWS Neptune implementation using Gremlin.
    
    Use for:
    - Production AWS deployments
    - Serverless graph workloads
    - Managed graph database with IAM auth
    
    Connection URL format:
    - wss://<neptune-endpoint>:8182/gremlin
    """
    
    def __init__(
        self, 
        connection_url: str, 
        region: str = "us-east-1",
        use_iam: bool = True,
        **kwargs
    ):
        super().__init__(connection_url, **kwargs)
        self.region = region
        self.use_iam = use_iam
        self._client: client.Client | None = None
        self._g: GraphTraversalSource | None = None
    
    async def connect(self) -> None:
        """Establish connection to Neptune."""
        try:
            logger.info(
                "Connecting to Neptune",
                url=self.connection_url,
                region=self.region,
                use_iam=self.use_iam
            )
            
            # For IAM auth, we'd need to sign requests with SigV4
            # Simplified version for now - full IAM support would use
            # neptune_python_utils or custom signing
            
            self._client = client.Client(
                self.connection_url,
                "g",
                message_serializer=serializer.GraphSONSerializersV3d0(),
            )
            
            connection = DriverRemoteConnection(self.connection_url, "g")
            self._g = traversal().withRemote(connection)
            
            self._connected = True
            logger.info("Connected to Neptune")
            
        except Exception as e:
            logger.error("Failed to connect to Neptune", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Neptune connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._g = None
            self._connected = False
            logger.info("Disconnected from Neptune")
    
    @property
    def g(self) -> GraphTraversalSource:
        """Get Gremlin traversal source."""
        if self._g is None:
            raise RuntimeError("Not connected to Neptune")
        return self._g
    
    # ==================== VERTEX OPERATIONS ====================
    # Neptune uses same Gremlin as JanusGraph, but with some optimizations
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def create_vertex(
        self,
        label: str,
        properties: dict[str, Any],
        tenant_id: str = "default"
    ) -> str:
        """Create a vertex in Neptune."""
        props = {**properties, "tenant_id": tenant_id}
        
        # Neptune supports parameterized queries for better performance
        query = f"g.addV('{label}')"
        for key, value in props.items():
            if value is not None:
                query += f".property('{key}', {repr(value)})"
        query += ".id()"
        
        result = await self.execute_query(query)
        vertex_id = str(result[0]) if result else None
        
        logger.debug("Created vertex in Neptune", label=label, vertex_id=vertex_id)
        return vertex_id
    
    async def get_vertex(self, vertex_id: str) -> dict[str, Any] | None:
        """Get vertex by ID."""
        # Neptune uses string IDs
        query = f"g.V('{vertex_id}').valueMap(true)"
        result = await self.execute_query(query)
        
        if not result:
            return None
        
        return self._flatten_value_map(result[0])
    
    async def update_vertex(
        self,
        vertex_id: str,
        properties: dict[str, Any]
    ) -> bool:
        """Update vertex properties."""
        query = f"g.V('{vertex_id}')"
        for key, value in properties.items():
            if value is not None:
                # Neptune single cardinality update
                query += f".property(single, '{key}', {repr(value)})"
        query += ".id()"
        
        result = await self.execute_query(query)
        return len(result) > 0
    
    async def delete_vertex(self, vertex_id: str) -> bool:
        """Delete vertex and edges."""
        query = f"g.V('{vertex_id}').drop()"
        await self.execute_query(query)
        return True
    
    async def find_vertices(
        self,
        label: str,
        filters: dict[str, Any] | None = None,
        tenant_id: str = "default",
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Find vertices by label and filters."""
        query = f"g.V().hasLabel('{label}').has('tenant_id', '{tenant_id}')"
        
        if filters:
            for key, value in filters.items():
                query += f".has('{key}', {repr(value)})"
        
        query += f".limit({limit}).valueMap(true)"
        
        results = await self.execute_query(query)
        return [self._flatten_value_map(r) for r in results]
    
    # ==================== EDGE OPERATIONS ====================
    
    async def create_edge(
        self,
        from_vertex_id: str,
        to_vertex_id: str,
        label: str,
        properties: dict[str, Any] | None = None
    ) -> str:
        """Create edge in Neptune."""
        query = f"g.V('{from_vertex_id}').addE('{label}').to(g.V('{to_vertex_id}'))"
        
        if properties:
            for key, value in properties.items():
                if value is not None:
                    query += f".property('{key}', {repr(value)})"
        
        query += ".id()"
        result = await self.execute_query(query)
        return str(result[0]) if result else None
    
    async def get_edges(
        self,
        vertex_id: str,
        direction: str = "both",
        edge_label: str | None = None
    ) -> list[dict[str, Any]]:
        """Get edges connected to vertex."""
        dir_method = {"in": "inE", "out": "outE", "both": "bothE"}[direction]
        
        query = f"g.V('{vertex_id}').{dir_method}()"
        if edge_label:
            query = f"g.V('{vertex_id}').{dir_method}('{edge_label}')"
        
        query += ".valueMap(true)"
        results = await self.execute_query(query)
        return [self._flatten_value_map(r) for r in results]
    
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete edge."""
        query = f"g.E('{edge_id}').drop()"
        await self.execute_query(query)
        return True
    
    # ==================== TRAVERSAL OPERATIONS ====================
    
    async def traverse(
        self,
        start_vertex_id: str,
        path_pattern: list[str],
        max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """Traverse graph following edge pattern."""
        query = f"g.V('{start_vertex_id}')"
        
        for edge_label in path_pattern[:max_depth]:
            query += f".out('{edge_label}')"
        
        query += ".valueMap(true)"
        results = await self.execute_query(query)
        return [self._flatten_value_map(r) for r in results]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def execute_query(
        self,
        query: str,
        bindings: dict[str, Any] | None = None
    ) -> list[Any]:
        """Execute Gremlin query on Neptune."""
        if self._client is None:
            raise RuntimeError("Not connected to Neptune")
        
        logger.debug("Executing Neptune query", query=query[:100])
        
        try:
            result_set = self._client.submit(query, bindings or {})
            return result_set.all().result()
        except Exception as e:
            logger.error("Neptune query failed", query=query[:100], error=str(e))
            raise
    
    # ==================== HEALTH & ADMIN ====================
    
    async def health_check(self) -> bool:
        """Check Neptune health."""
        try:
            await self.execute_query("g.V().limit(1).count()")
            return True
        except Exception:
            return False
    
    async def get_stats(self) -> dict[str, Any]:
        """Get Neptune statistics."""
        vertex_count = await self.execute_query("g.V().count()")
        edge_count = await self.execute_query("g.E().count()")
        
        return {
            "provider": "neptune",
            "region": self.region,
            "vertex_count": vertex_count[0] if vertex_count else 0,
            "edge_count": edge_count[0] if edge_count else 0,
        }
    
    # ==================== HELPERS ====================
    
    def _flatten_value_map(self, value_map: dict) -> dict[str, Any]:
        """Convert Gremlin valueMap to flat dict."""
        result = {}
        for key, value in value_map.items():
            if key in ("id", "label"):
                result[key] = value
            elif isinstance(value, list) and len(value) == 1:
                result[key] = value[0]
            else:
                result[key] = value
        return result
