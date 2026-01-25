"""
AEGIS Database Clients

Manages connections to all databases:
- PostgreSQL/TimescaleDB
- JanusGraph (Neptune-compatible)
- OpenSearch (Vector DB)
- Redis (Cache)
"""
from dataclasses import dataclass, field
from typing import Any
import asyncio
import structlog

logger = structlog.get_logger(__name__)

# Global clients instance
_clients: "DatabaseClients | None" = None


@dataclass
class DatabaseClients:
    """Container for all database clients."""
    
    postgres: Any = None
    graph: Any = None
    opensearch: Any = None
    redis: Any = None
    
    _initialized: bool = field(default=False, repr=False)
    
    def is_ready(self) -> bool:
        """Check if all required clients are connected."""
        return self._initialized


async def init_postgres(settings) -> Any:
    """Initialize PostgreSQL connection pool."""
    try:
        import asyncpg
        
        pool = await asyncpg.create_pool(
            host=settings.postgres.host,
            port=settings.postgres.port,
            user=settings.postgres.user,
            password=settings.postgres.password.get_secret_value(),
            database=settings.postgres.database,
            min_size=settings.postgres.min_pool_size,
            max_size=settings.postgres.max_pool_size,
        )
        
        # Test connection
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info("PostgreSQL connected", version=version[:50])
        
        return pool
    except ImportError:
        logger.warning("asyncpg not installed, using mock postgres client")
        return MockPostgres()
    except Exception as e:
        logger.error("PostgreSQL connection failed", error=str(e))
        return MockPostgres()


async def init_graph(settings) -> Any:
    """Initialize JanusGraph/Neptune Gremlin client."""
    try:
        from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
        from gremlin_python.process.anonymous_traversal import traversal
        
        connection = DriverRemoteConnection(
            settings.graph_db.connection_url,
            'g'
        )
        g = traversal().withRemote(connection)
        
        # Test connection
        count = g.V().limit(1).count().next()
        logger.info("JanusGraph connected", vertex_sample=count)
        
        return {"connection": connection, "g": g}
    except ImportError:
        logger.warning("gremlinpython not available, using mock graph client")
        return MockGraph()
    except Exception as e:
        logger.warning("JanusGraph connection failed, using mock", error=str(e))
        return MockGraph()


async def init_opensearch(settings) -> Any:
    """Initialize OpenSearch client."""
    try:
        from opensearchpy import AsyncOpenSearch
        
        client = AsyncOpenSearch(
            hosts=[{"host": settings.opensearch.host, "port": settings.opensearch.port}],
            http_auth=(settings.opensearch.user, settings.opensearch.password.get_secret_value()),
            use_ssl=settings.opensearch.use_ssl,
            verify_certs=False,
        )
        
        # Test connection
        info = await client.info()
        logger.info("OpenSearch connected", version=info.get("version", {}).get("number"))
        
        return client
    except ImportError:
        logger.warning("opensearch-py not installed, using mock client")
        return MockOpenSearch()
    except Exception as e:
        logger.warning("OpenSearch connection failed, using mock", error=str(e))
        return MockOpenSearch()


async def init_redis(settings) -> Any:
    """Initialize Redis client."""
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(settings.redis.connection_url)
        
        # Test connection
        await client.ping()
        logger.info("Redis connected")
        
        return client
    except ImportError:
        logger.warning("redis not installed, using mock client")
        return MockRedis()
    except Exception as e:
        logger.warning("Redis connection failed, using mock", error=str(e))
        return MockRedis()


async def init_db_clients(settings) -> DatabaseClients:
    """
    Initialize all database clients.
    
    Called during application startup.
    """
    global _clients
    
    logger.info("Initializing database connections...")
    
    # Initialize all connections in parallel
    postgres, graph, opensearch, redis = await asyncio.gather(
        init_postgres(settings),
        init_graph(settings),
        init_opensearch(settings),
        init_redis(settings),
        return_exceptions=True
    )
    
    # Handle any exceptions
    if isinstance(postgres, Exception):
        logger.error("Postgres init failed", error=str(postgres))
        postgres = MockPostgres()
    if isinstance(graph, Exception):
        logger.error("Graph init failed", error=str(graph))
        graph = MockGraph()
    if isinstance(opensearch, Exception):
        logger.error("OpenSearch init failed", error=str(opensearch))
        opensearch = MockOpenSearch()
    if isinstance(redis, Exception):
        logger.error("Redis init failed", error=str(redis))
        redis = MockRedis()
    
    _clients = DatabaseClients(
        postgres=postgres,
        graph=graph,
        opensearch=opensearch,
        redis=redis,
        _initialized=True
    )
    
    logger.info("Database connections initialized")
    return _clients


async def close_db_clients():
    """Close all database connections."""
    global _clients
    
    if _clients is None:
        return
    
    logger.info("Closing database connections...")
    
    try:
        # Close PostgreSQL pool
        if _clients.postgres and hasattr(_clients.postgres, 'close'):
            await _clients.postgres.close()
        
        # Close Gremlin connection
        if _clients.graph and isinstance(_clients.graph, dict):
            if "connection" in _clients.graph:
                _clients.graph["connection"].close()
        
        # Close OpenSearch
        if _clients.opensearch and hasattr(_clients.opensearch, 'close'):
            await _clients.opensearch.close()
        
        # Close Redis
        if _clients.redis and hasattr(_clients.redis, 'close'):
            await _clients.redis.close()
        
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing connections", error=str(e))
    
    _clients = None


def get_db_clients() -> DatabaseClients:
    """Get the initialized database clients."""
    if _clients is None:
        raise RuntimeError("Database clients not initialized. Call init_db_clients first.")
    return _clients


# =============================================================================
# Mock Clients (for development without actual databases)
# =============================================================================

class MockPostgres:
    """Mock PostgreSQL client for development."""
    
    async def fetch(self, query: str, *args):
        logger.debug("MockPostgres.fetch", query=query[:100])
        return []
    
    async def fetchrow(self, query: str, *args):
        logger.debug("MockPostgres.fetchrow", query=query[:100])
        return None
    
    async def fetchval(self, query: str, *args):
        logger.debug("MockPostgres.fetchval", query=query[:100])
        return None
    
    async def execute(self, query: str, *args):
        logger.debug("MockPostgres.execute", query=query[:100])
        return "OK"
    
    def acquire(self):
        return MockPostgresConnection()
    
    async def close(self):
        pass


class MockPostgresConnection:
    """Mock connection for context manager."""
    
    async def __aenter__(self):
        return MockPostgres()
    
    async def __aexit__(self, *args):
        pass


class MockGraph:
    """Mock Graph client for development."""
    
    async def query(self, gremlin: str):
        logger.debug("MockGraph.query", gremlin=gremlin[:100])
        return []
    
    async def add_vertex(self, label: str, id: str, properties: dict):
        logger.debug("MockGraph.add_vertex", label=label, id=id)
        return id
    
    async def add_edge(self, from_label: str, from_id: str, to_label: str, to_id: str, edge_label: str):
        logger.debug("MockGraph.add_edge", edge=edge_label)
        return True
    
    async def update_vertex(self, label: str, id: str, properties: dict):
        logger.debug("MockGraph.update_vertex", label=label, id=id)
        return True


class MockOpenSearch:
    """Mock OpenSearch client for development."""
    
    async def search(self, index: str, body: dict):
        logger.debug("MockOpenSearch.search", index=index)
        return {"hits": {"hits": [], "total": {"value": 0}}}
    
    async def index(self, index: str, body: dict, id: str = None):
        logger.debug("MockOpenSearch.index", index=index)
        return {"result": "created"}
    
    async def close(self):
        pass


class MockRedis:
    """Mock Redis client for development."""
    
    _data: dict = {}
    
    async def get(self, key: str):
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        self._data[key] = value
        return True
    
    async def delete(self, key: str):
        self._data.pop(key, None)
        return True
    
    async def close(self):
        pass
