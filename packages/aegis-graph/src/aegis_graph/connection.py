"""
Graph Connection Management

Production-grade connection pooling and management for JanusGraph.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
import structlog

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.driver.aiohttp.transport import AiohttpTransport
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import GraphTraversalSource

logger = structlog.get_logger(__name__)


class GraphConnectionPool:
    """
    Connection pool for JanusGraph.
    
    Manages multiple connections for concurrent graph operations.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8182,
        pool_size: int = 10,
        max_content_length: int = 65536000,
        traversal_source: str = "g",
    ):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.max_content_length = max_content_length
        self.traversal_source = traversal_source
        
        self._url = f"ws://{host}:{port}/gremlin"
        self._connections: list[DriverRemoteConnection] = []
        self._available: asyncio.Queue[DriverRemoteConnection] = asyncio.Queue()
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info(
                "Initializing graph connection pool",
                url=self._url,
                pool_size=self.pool_size
            )
            
            for i in range(self.pool_size):
                try:
                    conn = await self._create_connection()
                    self._connections.append(conn)
                    await self._available.put(conn)
                except Exception as e:
                    logger.error(f"Failed to create connection {i}", error=str(e))
                    raise
            
            self._initialized = True
            logger.info("Graph connection pool initialized", connections=len(self._connections))
    
    async def _create_connection(self) -> DriverRemoteConnection:
        """Create a new connection."""
        transport = AiohttpTransport(
            call_from_event_loop=True,
            read_timeout=30,
            write_timeout=30,
        )
        
        return DriverRemoteConnection(
            self._url,
            self.traversal_source,
            transport_factory=lambda: transport,
        )
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[DriverRemoteConnection]:
        """
        Get a connection from the pool.
        
        Usage:
            async with pool.get_connection() as conn:
                g = traversal().withRemote(conn)
                result = await g.V().count().next()
        """
        if not self._initialized:
            await self.initialize()
        
        conn = await self._available.get()
        try:
            yield conn
        finally:
            await self._available.put(conn)
    
    @asynccontextmanager
    async def get_traversal(self) -> AsyncIterator[GraphTraversalSource]:
        """
        Get a graph traversal source from the pool.
        
        Usage:
            async with pool.get_traversal() as g:
                result = await g.V().count().next()
        """
        async with self.get_connection() as conn:
            g = traversal().withRemote(conn)
            yield g
    
    async def close(self) -> None:
        """Close all connections in the pool."""
        logger.info("Closing graph connection pool")
        
        for conn in self._connections:
            try:
                await conn.close()
            except Exception as e:
                logger.warning("Error closing connection", error=str(e))
        
        self._connections.clear()
        self._initialized = False
        logger.info("Graph connection pool closed")
    
    async def health_check(self) -> dict:
        """Check pool health."""
        try:
            async with self.get_traversal() as g:
                count = await g.V().limit(1).count().next()
                return {
                    "status": "healthy",
                    "pool_size": self.pool_size,
                    "available": self._available.qsize(),
                    "test_query": "success"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global connection pool
_pool: GraphConnectionPool | None = None


async def get_graph_pool(
    host: str = "localhost",
    port: int = 8182,
    pool_size: int = 10,
) -> GraphConnectionPool:
    """Get or create the global connection pool."""
    global _pool
    
    if _pool is None:
        _pool = GraphConnectionPool(
            host=host,
            port=port,
            pool_size=pool_size,
        )
        await _pool.initialize()
    
    return _pool


async def close_graph_pool() -> None:
    """Close the global connection pool."""
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
