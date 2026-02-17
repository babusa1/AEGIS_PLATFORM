"""
VeritOS Database Clients

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
    dynamodb: Any = None
    
    _initialized: bool = field(default=False, repr=False)
    
    def is_ready(self) -> bool:
        """Check if all required clients are connected."""
        return self._initialized


async def init_postgres(settings) -> Any:
    """Initialize PostgreSQL connection pool."""
    mock_mode = settings.app.mock_mode
    
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
        if not mock_mode:
            raise RuntimeError("asyncpg not installed and MOCK_MODE=false - cannot proceed")
        logger.warning("asyncpg not installed, using mock postgres client (MOCK_MODE=true)")
        return MockPostgres()
    except Exception as e:
        if not mock_mode:
            logger.error("PostgreSQL connection failed and MOCK_MODE=false - failing fast", error=str(e))
            raise RuntimeError(f"PostgreSQL connection failed: {str(e)}") from e
        logger.warning("PostgreSQL connection failed, using mock client (MOCK_MODE=true)", error=str(e))
        return MockPostgres()


async def init_graph(settings) -> Any:
    """Initialize JanusGraph/Neptune Gremlin client."""
    mock_mode = settings.app.mock_mode
    
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
        if not mock_mode:
            raise RuntimeError("gremlinpython not available and MOCK_MODE=false - cannot proceed")
        logger.warning("gremlinpython not available, using mock graph client (MOCK_MODE=true)")
        return MockGraph()
    except Exception as e:
        if not mock_mode:
            logger.error("JanusGraph connection failed and MOCK_MODE=false - failing fast", error=str(e))
            raise RuntimeError(f"JanusGraph connection failed: {str(e)}") from e
        logger.warning("JanusGraph connection failed, using mock (MOCK_MODE=true)", error=str(e))
        return MockGraph()


async def init_opensearch(settings) -> Any:
    """Initialize OpenSearch client."""
    mock_mode = settings.app.mock_mode
    
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
        if not mock_mode:
            raise RuntimeError("opensearch-py not installed and MOCK_MODE=false - cannot proceed")
        logger.warning("opensearch-py not installed, using mock client (MOCK_MODE=true)")
        return MockOpenSearch()
    except Exception as e:
        if not mock_mode:
            logger.error("OpenSearch connection failed and MOCK_MODE=false - failing fast", error=str(e))
            raise RuntimeError(f"OpenSearch connection failed: {str(e)}") from e
        logger.warning("OpenSearch connection failed, using mock (MOCK_MODE=true)", error=str(e))
        return MockOpenSearch()


async def init_redis(settings) -> Any:
    """Initialize Redis client."""
    mock_mode = settings.app.mock_mode
    
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(settings.redis.connection_url)
        
        # Test connection
        await client.ping()
        logger.info("Redis connected")
        
        return client
    except ImportError:
        if not mock_mode:
            raise RuntimeError("redis not installed and MOCK_MODE=false - cannot proceed")
        logger.warning("redis not installed, using mock client (MOCK_MODE=true)")
        return MockRedis()
    except Exception as e:
        if not mock_mode:
            logger.error("Redis connection failed and MOCK_MODE=false - failing fast", error=str(e))
            raise RuntimeError(f"Redis connection failed: {str(e)}") from e
        logger.warning("Redis connection failed, using mock (MOCK_MODE=true)", error=str(e))
        return MockRedis()


async def init_dynamodb(settings) -> Any:
    """Initialize DynamoDB client."""
    mock_mode = settings.app.mock_mode
    
    try:
        from aegis.db.dynamodb import DynamoDBClient, MockDynamoDBClient
        
        if hasattr(settings, 'dynamodb'):
            client = DynamoDBClient(
                region=settings.dynamodb.region,
                endpoint_url=settings.dynamodb.endpoint_url,
                table_prefix=settings.dynamodb.table_prefix,
            )
            
            connected = await client.connect()
            if connected:
                await client.create_tables()
                logger.info("DynamoDB connected")
                return client
        
        # Fall back to mock
        if not mock_mode:
            raise RuntimeError("DynamoDB not connected and MOCK_MODE=false - cannot proceed")
        logger.warning("Using mock DynamoDB client (MOCK_MODE=true)")
        mock_client = MockDynamoDBClient()
        await mock_client.connect()
        return mock_client
        
    except ImportError:
        if not mock_mode:
            raise RuntimeError("DynamoDB dependencies not installed and MOCK_MODE=false - cannot proceed")
        logger.warning("DynamoDB dependencies not installed, using mock client (MOCK_MODE=true)")
        from aegis.db.dynamodb import MockDynamoDBClient
        mock_client = MockDynamoDBClient()
        await mock_client.connect()
        return mock_client
    except Exception as e:
        if not mock_mode and not isinstance(e, RuntimeError):
            logger.error("DynamoDB connection failed and MOCK_MODE=false - failing fast", error=str(e))
            raise RuntimeError(f"DynamoDB connection failed: {str(e)}") from e
        logger.warning("DynamoDB connection failed, using mock (MOCK_MODE=true)", error=str(e))
        from aegis.db.dynamodb import MockDynamoDBClient
        mock_client = MockDynamoDBClient()
        await mock_client.connect()
        return mock_client


async def init_db_clients(settings) -> DatabaseClients:
    """
    Initialize all database clients.
    
    Called during application startup.
    """
    global _clients
    
    mock_mode = settings.app.mock_mode
    logger.info("Initializing database connections...", mock_mode=mock_mode)
    
    # Initialize all connections in parallel
    postgres, graph, opensearch, redis, dynamodb = await asyncio.gather(
        init_postgres(settings),
        init_graph(settings),
        init_opensearch(settings),
        init_redis(settings),
        init_dynamodb(settings),
        return_exceptions=True
    )
    
    # Handle any exceptions based on MOCK_MODE
    if isinstance(postgres, Exception):
        if not mock_mode:
            logger.error("Postgres init failed and MOCK_MODE=false - failing", error=str(postgres))
            raise RuntimeError(f"PostgreSQL initialization failed: {postgres}") from postgres
        logger.warning("Postgres init failed, using mock (MOCK_MODE=true)", error=str(postgres))
        postgres = MockPostgres()
    if isinstance(graph, Exception):
        if not mock_mode:
            logger.error("Graph init failed and MOCK_MODE=false - failing", error=str(graph))
            raise RuntimeError(f"Graph DB initialization failed: {graph}") from graph
        logger.warning("Graph init failed, using mock (MOCK_MODE=true)", error=str(graph))
        graph = MockGraph()
    if isinstance(opensearch, Exception):
        if not mock_mode:
            logger.error("OpenSearch init failed and MOCK_MODE=false - failing", error=str(opensearch))
            raise RuntimeError(f"OpenSearch initialization failed: {opensearch}") from opensearch
        logger.warning("OpenSearch init failed, using mock (MOCK_MODE=true)", error=str(opensearch))
        opensearch = MockOpenSearch()
    if isinstance(redis, Exception):
        if not mock_mode:
            logger.error("Redis init failed and MOCK_MODE=false - failing", error=str(redis))
            raise RuntimeError(f"Redis initialization failed: {redis}") from redis
        logger.warning("Redis init failed, using mock (MOCK_MODE=true)", error=str(redis))
        redis = MockRedis()
    if isinstance(dynamodb, Exception):
        if not mock_mode:
            logger.error("DynamoDB init failed and MOCK_MODE=false - failing", error=str(dynamodb))
            raise RuntimeError(f"DynamoDB initialization failed: {dynamodb}") from dynamodb
        logger.warning("DynamoDB init failed, using mock (MOCK_MODE=true)", error=str(dynamodb))
        from aegis.db.dynamodb import MockDynamoDBClient
        dynamodb = MockDynamoDBClient()
    
    # Check if any are mocks and log warning
    mock_count = sum([
        isinstance(postgres, MockPostgres),
        isinstance(graph, MockGraph),
        isinstance(opensearch, MockOpenSearch),
        isinstance(redis, MockRedis),
    ])
    
    if mock_count > 0:
        logger.warning(
            f"Using {mock_count} mock client(s) (MOCK_MODE={mock_mode})",
            postgres_mock=isinstance(postgres, MockPostgres),
            graph_mock=isinstance(graph, MockGraph),
            opensearch_mock=isinstance(opensearch, MockOpenSearch),
            redis_mock=isinstance(redis, MockRedis),
        )
    
    _clients = DatabaseClients(
        postgres=postgres,
        graph=graph,
        opensearch=opensearch,
        redis=redis,
        dynamodb=dynamodb,
        _initialized=True
    )
    
    logger.info("Database connections initialized", mock_count=mock_count)
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


def get_postgres_pool():
    """
    Get the PostgreSQL connection pool.
    
    Returns:
        asyncpg.Pool or None if not available
    """
    global _clients
    if _clients is None:
        return None
    return _clients.postgres


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
