"""
Graph Database Client

Gremlin client for Neptune/JanusGraph with connection pooling and retry logic.
"""

from typing import Any

import structlog
from gremlin_python.driver import client, serializer
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import GraphTraversalSource
from tenacity import retry, stop_after_attempt, wait_exponential

from aegis.config import get_settings

logger = structlog.get_logger(__name__)


class GraphClient:
    """
    Gremlin graph database client.
    
    Supports both Neptune and JanusGraph (for local development).
    
    Usage:
        async with GraphClient() as client:
            result = await client.execute("g.V().count()")
    """
    
    def __init__(self):
        self.settings = get_settings().graph_db
        self._client: client.Client | None = None
        self._g: GraphTraversalSource | None = None
    
    @property
    def connection_url(self) -> str:
        """Get the Gremlin connection URL."""
        return self.settings.connection_url
    
    async def connect(self) -> None:
        """Establish connection to the graph database."""
        try:
            logger.info(
                "Connecting to graph database",
                url=self.connection_url,
            )
            
            self._client = client.Client(
                self.connection_url,
                "g",
                message_serializer=serializer.GraphSONSerializersV3d0(),
            )
            
            # Also create a traversal source for fluent API
            connection = DriverRemoteConnection(
                self.connection_url,
                "g",
            )
            self._g = traversal().withRemote(connection)
            
            logger.info("Connected to graph database")
            
        except Exception as e:
            logger.error("Failed to connect to graph database", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close the graph database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._g = None
            logger.info("Disconnected from graph database")
    
    async def __aenter__(self) -> "GraphClient":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
    
    @property
    def g(self) -> GraphTraversalSource:
        """Get the Gremlin traversal source for fluent queries."""
        if self._g is None:
            raise RuntimeError("Graph client not connected. Call connect() first.")
        return self._g
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def execute(self, query: str, bindings: dict[str, Any] | None = None) -> list[Any]:
        """
        Execute a Gremlin query string.
        
        Args:
            query: Gremlin query string
            bindings: Optional parameter bindings
            
        Returns:
            List of results
        """
        if self._client is None:
            raise RuntimeError("Graph client not connected. Call connect() first.")
        
        logger.debug("Executing Gremlin query", query=query[:100])
        
        try:
            result_set = self._client.submit(query, bindings or {})
            results = result_set.all().result()
            return results
        except Exception as e:
            logger.error("Gremlin query failed", query=query[:100], error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if the graph database is healthy."""
        try:
            result = await self.execute("g.V().limit(1).count()")
            return True
        except Exception:
            return False


# Singleton instance for the application
_graph_client: GraphClient | None = None


async def get_graph_client() -> GraphClient:
    """Get the singleton graph client instance."""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphClient()
        await _graph_client.connect()
    return _graph_client


async def close_graph_client() -> None:
    """Close the singleton graph client."""
    global _graph_client
    if _graph_client is not None:
        await _graph_client.disconnect()
        _graph_client = None
