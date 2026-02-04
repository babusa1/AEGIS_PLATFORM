"""
AEGIS DynamoDB Client

Production-ready DynamoDB client for workflow state persistence,
session management, and high-throughput key-value storage.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from enum import Enum
import asyncio
import json
import structlog

logger = structlog.get_logger(__name__)

# Global client instance
_dynamodb_client: "DynamoDBClient | None" = None


class DynamoDBTableType(str, Enum):
    """Table types for AEGIS DynamoDB usage."""
    WORKFLOW_STATE = "workflow_state"
    AGENT_SESSIONS = "agent_sessions"
    EXECUTION_CHECKPOINTS = "execution_checkpoints"
    CACHE = "cache"


@dataclass
class DynamoDBItem:
    """Represents a DynamoDB item."""
    pk: str  # Partition key
    sk: str  # Sort key
    data: dict[str, Any]
    ttl: int | None = None  # Unix timestamp for TTL
    created_at: str | None = None
    updated_at: str | None = None


class DynamoDBClient:
    """
    Async DynamoDB client for AEGIS.
    
    Provides high-level operations for:
    - Workflow state persistence
    - Agent session management
    - Execution checkpoints
    - General key-value caching with TTL
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        table_prefix: str = "aegis",
    ):
        self.region = region
        self.endpoint_url = endpoint_url
        self.table_prefix = table_prefix
        self._client = None
        self._resource = None
        self._tables: dict[str, Any] = {}
    
    async def connect(self) -> bool:
        """Initialize DynamoDB connection."""
        try:
            import aioboto3
            
            session = aioboto3.Session()
            
            # Create client for low-level operations
            client_kwargs = {"region_name": self.region}
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            
            self._session = session
            self._client_kwargs = client_kwargs
            
            # Test connection
            async with session.client("dynamodb", **client_kwargs) as client:
                response = await client.list_tables(Limit=1)
                logger.info(
                    "DynamoDB connected",
                    region=self.region,
                    endpoint=self.endpoint_url or "AWS",
                    tables=response.get("TableNames", [])
                )
            
            return True
            
        except ImportError:
            logger.warning("aioboto3 not installed, using mock DynamoDB client")
            return False
        except Exception as e:
            logger.error("DynamoDB connection failed", error=str(e))
            return False
    
    def _get_table_name(self, table_type: DynamoDBTableType) -> str:
        """Get full table name with prefix."""
        return f"{self.table_prefix}_{table_type.value}"
    
    async def create_tables(self) -> dict[str, bool]:
        """Create all required tables if they don't exist."""
        results = {}
        
        table_definitions = [
            {
                "type": DynamoDBTableType.WORKFLOW_STATE,
                "key_schema": [
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                "attributes": [
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
                "gsi": [
                    {
                        "IndexName": "status-index",
                        "KeySchema": [
                            {"AttributeName": "status", "KeyType": "HASH"},
                            {"AttributeName": "updated_at", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
            },
            {
                "type": DynamoDBTableType.AGENT_SESSIONS,
                "key_schema": [
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                "attributes": [
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
            },
            {
                "type": DynamoDBTableType.EXECUTION_CHECKPOINTS,
                "key_schema": [
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                "attributes": [
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
            },
            {
                "type": DynamoDBTableType.CACHE,
                "key_schema": [
                    {"AttributeName": "pk", "KeyType": "HASH"},
                ],
                "attributes": [
                    {"AttributeName": "pk", "AttributeType": "S"},
                ],
            },
        ]
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                existing_tables = (await client.list_tables())["TableNames"]
                
                for table_def in table_definitions:
                    table_name = self._get_table_name(table_def["type"])
                    
                    if table_name in existing_tables:
                        results[table_name] = True
                        logger.debug(f"Table {table_name} already exists")
                        continue
                    
                    try:
                        create_params = {
                            "TableName": table_name,
                            "KeySchema": table_def["key_schema"],
                            "AttributeDefinitions": table_def["attributes"],
                            "BillingMode": "PAY_PER_REQUEST",
                        }
                        
                        # Add GSI if defined
                        if "gsi" in table_def:
                            # Add GSI attributes
                            gsi_attrs = []
                            for gsi in table_def["gsi"]:
                                for key in gsi["KeySchema"]:
                                    attr_name = key["AttributeName"]
                                    if not any(a["AttributeName"] == attr_name for a in create_params["AttributeDefinitions"]):
                                        gsi_attrs.append({"AttributeName": attr_name, "AttributeType": "S"})
                            create_params["AttributeDefinitions"].extend(gsi_attrs)
                            create_params["GlobalSecondaryIndexes"] = table_def["gsi"]
                        
                        await client.create_table(**create_params)
                        
                        # Enable TTL for cache table
                        if table_def["type"] == DynamoDBTableType.CACHE:
                            await asyncio.sleep(5)  # Wait for table to be active
                            await client.update_time_to_live(
                                TableName=table_name,
                                TimeToLiveSpecification={
                                    "Enabled": True,
                                    "AttributeName": "ttl"
                                }
                            )
                        
                        results[table_name] = True
                        logger.info(f"Created table {table_name}")
                        
                    except Exception as e:
                        results[table_name] = False
                        logger.error(f"Failed to create table {table_name}", error=str(e))
                        
        except Exception as e:
            logger.error("Failed to create tables", error=str(e))
        
        return results
    
    # ==========================================================================
    # Core CRUD Operations
    # ==========================================================================
    
    async def put_item(
        self,
        table_type: DynamoDBTableType,
        item: DynamoDBItem,
    ) -> bool:
        """Put an item into DynamoDB."""
        table_name = self._get_table_name(table_type)
        
        now = datetime.now(timezone.utc).isoformat()
        
        dynamo_item = {
            "pk": {"S": item.pk},
            "sk": {"S": item.sk},
            "data": {"S": json.dumps(item.data)},
            "created_at": {"S": item.created_at or now},
            "updated_at": {"S": now},
        }
        
        if item.ttl:
            dynamo_item["ttl"] = {"N": str(item.ttl)}
        
        # Add any top-level fields from data for GSI
        for key, value in item.data.items():
            if key not in dynamo_item and isinstance(value, str):
                dynamo_item[key] = {"S": value}
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                await client.put_item(
                    TableName=table_name,
                    Item=dynamo_item,
                )
                return True
        except Exception as e:
            logger.error("DynamoDB put_item failed", table=table_name, error=str(e))
            return False
    
    async def get_item(
        self,
        table_type: DynamoDBTableType,
        pk: str,
        sk: str | None = None,
    ) -> DynamoDBItem | None:
        """Get an item from DynamoDB."""
        table_name = self._get_table_name(table_type)
        
        key = {"pk": {"S": pk}}
        if sk:
            key["sk"] = {"S": sk}
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                response = await client.get_item(
                    TableName=table_name,
                    Key=key,
                )
                
                item = response.get("Item")
                if not item:
                    return None
                
                return DynamoDBItem(
                    pk=item["pk"]["S"],
                    sk=item.get("sk", {}).get("S", ""),
                    data=json.loads(item["data"]["S"]),
                    ttl=int(item["ttl"]["N"]) if "ttl" in item else None,
                    created_at=item.get("created_at", {}).get("S"),
                    updated_at=item.get("updated_at", {}).get("S"),
                )
        except Exception as e:
            logger.error("DynamoDB get_item failed", table=table_name, error=str(e))
            return None
    
    async def delete_item(
        self,
        table_type: DynamoDBTableType,
        pk: str,
        sk: str | None = None,
    ) -> bool:
        """Delete an item from DynamoDB."""
        table_name = self._get_table_name(table_type)
        
        key = {"pk": {"S": pk}}
        if sk:
            key["sk"] = {"S": sk}
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                await client.delete_item(
                    TableName=table_name,
                    Key=key,
                )
                return True
        except Exception as e:
            logger.error("DynamoDB delete_item failed", table=table_name, error=str(e))
            return False
    
    async def query(
        self,
        table_type: DynamoDBTableType,
        pk: str,
        sk_prefix: str | None = None,
        limit: int = 100,
        scan_forward: bool = True,
    ) -> list[DynamoDBItem]:
        """Query items by partition key and optional sort key prefix."""
        table_name = self._get_table_name(table_type)
        
        key_condition = "pk = :pk"
        expression_values = {":pk": {"S": pk}}
        
        if sk_prefix:
            key_condition += " AND begins_with(sk, :sk_prefix)"
            expression_values[":sk_prefix"] = {"S": sk_prefix}
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                response = await client.query(
                    TableName=table_name,
                    KeyConditionExpression=key_condition,
                    ExpressionAttributeValues=expression_values,
                    Limit=limit,
                    ScanIndexForward=scan_forward,
                )
                
                items = []
                for item in response.get("Items", []):
                    items.append(DynamoDBItem(
                        pk=item["pk"]["S"],
                        sk=item.get("sk", {}).get("S", ""),
                        data=json.loads(item["data"]["S"]),
                        ttl=int(item["ttl"]["N"]) if "ttl" in item else None,
                        created_at=item.get("created_at", {}).get("S"),
                        updated_at=item.get("updated_at", {}).get("S"),
                    ))
                
                return items
        except Exception as e:
            logger.error("DynamoDB query failed", table=table_name, error=str(e))
            return []
    
    # ==========================================================================
    # Batch Operations
    # ==========================================================================
    
    async def batch_put_items(
        self,
        table_type: DynamoDBTableType,
        items: list[DynamoDBItem],
    ) -> int:
        """Batch put items (up to 25 per batch)."""
        table_name = self._get_table_name(table_type)
        now = datetime.now(timezone.utc).isoformat()
        
        # DynamoDB allows max 25 items per batch
        batches = [items[i:i+25] for i in range(0, len(items), 25)]
        success_count = 0
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                for batch in batches:
                    request_items = {
                        table_name: [
                            {
                                "PutRequest": {
                                    "Item": {
                                        "pk": {"S": item.pk},
                                        "sk": {"S": item.sk},
                                        "data": {"S": json.dumps(item.data)},
                                        "created_at": {"S": item.created_at or now},
                                        "updated_at": {"S": now},
                                        **({"ttl": {"N": str(item.ttl)}} if item.ttl else {}),
                                    }
                                }
                            }
                            for item in batch
                        ]
                    }
                    
                    response = await client.batch_write_item(RequestItems=request_items)
                    
                    # Handle unprocessed items
                    unprocessed = response.get("UnprocessedItems", {}).get(table_name, [])
                    success_count += len(batch) - len(unprocessed)
                    
                    if unprocessed:
                        logger.warning(
                            "Some items were not processed",
                            unprocessed_count=len(unprocessed)
                        )
        except Exception as e:
            logger.error("DynamoDB batch_put_items failed", error=str(e))
        
        return success_count
    
    async def batch_get_items(
        self,
        table_type: DynamoDBTableType,
        keys: list[tuple[str, str]],  # List of (pk, sk) tuples
    ) -> list[DynamoDBItem]:
        """Batch get items (up to 100 per batch)."""
        table_name = self._get_table_name(table_type)
        
        # DynamoDB allows max 100 items per batch get
        batches = [keys[i:i+100] for i in range(0, len(keys), 100)]
        all_items = []
        
        try:
            async with self._session.client("dynamodb", **self._client_kwargs) as client:
                for batch in batches:
                    request_items = {
                        table_name: {
                            "Keys": [
                                {"pk": {"S": pk}, "sk": {"S": sk}}
                                for pk, sk in batch
                            ]
                        }
                    }
                    
                    response = await client.batch_get_item(RequestItems=request_items)
                    
                    for item in response.get("Responses", {}).get(table_name, []):
                        all_items.append(DynamoDBItem(
                            pk=item["pk"]["S"],
                            sk=item.get("sk", {}).get("S", ""),
                            data=json.loads(item["data"]["S"]),
                            ttl=int(item["ttl"]["N"]) if "ttl" in item else None,
                            created_at=item.get("created_at", {}).get("S"),
                            updated_at=item.get("updated_at", {}).get("S"),
                        ))
        except Exception as e:
            logger.error("DynamoDB batch_get_items failed", error=str(e))
        
        return all_items
    
    # ==========================================================================
    # Workflow State Operations
    # ==========================================================================
    
    async def save_workflow_state(
        self,
        workflow_id: str,
        execution_id: str,
        state: dict[str, Any],
        status: str = "running",
    ) -> bool:
        """Save workflow execution state."""
        item = DynamoDBItem(
            pk=f"WORKFLOW#{workflow_id}",
            sk=f"EXEC#{execution_id}",
            data={
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "state": state,
                "status": status,
            }
        )
        return await self.put_item(DynamoDBTableType.WORKFLOW_STATE, item)
    
    async def get_workflow_state(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Get workflow execution state."""
        item = await self.get_item(
            DynamoDBTableType.WORKFLOW_STATE,
            pk=f"WORKFLOW#{workflow_id}",
            sk=f"EXEC#{execution_id}",
        )
        return item.data if item else None
    
    async def list_workflow_executions(
        self,
        workflow_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List all executions for a workflow."""
        items = await self.query(
            DynamoDBTableType.WORKFLOW_STATE,
            pk=f"WORKFLOW#{workflow_id}",
            sk_prefix="EXEC#",
            limit=limit,
            scan_forward=False,  # Most recent first
        )
        return [item.data for item in items]
    
    # ==========================================================================
    # Agent Session Operations
    # ==========================================================================
    
    async def save_agent_session(
        self,
        agent_id: str,
        session_id: str,
        session_data: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> bool:
        """Save agent session with TTL."""
        ttl = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds
        
        item = DynamoDBItem(
            pk=f"AGENT#{agent_id}",
            sk=f"SESSION#{session_id}",
            data=session_data,
            ttl=ttl,
        )
        return await self.put_item(DynamoDBTableType.AGENT_SESSIONS, item)
    
    async def get_agent_session(
        self,
        agent_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Get agent session."""
        item = await self.get_item(
            DynamoDBTableType.AGENT_SESSIONS,
            pk=f"AGENT#{agent_id}",
            sk=f"SESSION#{session_id}",
        )
        return item.data if item else None
    
    # ==========================================================================
    # Checkpoint Operations
    # ==========================================================================
    
    async def save_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str,
        checkpoint_data: dict[str, Any],
    ) -> bool:
        """Save execution checkpoint for crash recovery."""
        item = DynamoDBItem(
            pk=f"EXEC#{execution_id}",
            sk=f"CHECKPOINT#{checkpoint_id}",
            data=checkpoint_data,
        )
        return await self.put_item(DynamoDBTableType.EXECUTION_CHECKPOINTS, item)
    
    async def get_latest_checkpoint(
        self,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Get the latest checkpoint for an execution."""
        items = await self.query(
            DynamoDBTableType.EXECUTION_CHECKPOINTS,
            pk=f"EXEC#{execution_id}",
            sk_prefix="CHECKPOINT#",
            limit=1,
            scan_forward=False,
        )
        return items[0].data if items else None
    
    # ==========================================================================
    # Cache Operations
    # ==========================================================================
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> bool:
        """Set a cache value with TTL."""
        ttl = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds
        
        item = DynamoDBItem(
            pk=f"CACHE#{key}",
            sk="VALUE",
            data={"value": value},
            ttl=ttl,
        )
        return await self.put_item(DynamoDBTableType.CACHE, item)
    
    async def cache_get(self, key: str) -> Any | None:
        """Get a cache value."""
        item = await self.get_item(
            DynamoDBTableType.CACHE,
            pk=f"CACHE#{key}",
            sk="VALUE",
        )
        if item and item.data:
            return item.data.get("value")
        return None
    
    async def cache_delete(self, key: str) -> bool:
        """Delete a cache value."""
        return await self.delete_item(
            DynamoDBTableType.CACHE,
            pk=f"CACHE#{key}",
            sk="VALUE",
        )
    
    async def close(self):
        """Close the client (cleanup if needed)."""
        logger.info("DynamoDB client closed")


# =============================================================================
# Mock Client for Development
# =============================================================================

class MockDynamoDBClient(DynamoDBClient):
    """Mock DynamoDB client for development without AWS."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._storage: dict[str, dict[str, DynamoDBItem]] = {}
    
    async def connect(self) -> bool:
        logger.info("Using mock DynamoDB client")
        return True
    
    async def create_tables(self) -> dict[str, bool]:
        for table_type in DynamoDBTableType:
            table_name = self._get_table_name(table_type)
            self._storage[table_name] = {}
        return {self._get_table_name(t): True for t in DynamoDBTableType}
    
    async def put_item(self, table_type: DynamoDBTableType, item: DynamoDBItem) -> bool:
        table_name = self._get_table_name(table_type)
        if table_name not in self._storage:
            self._storage[table_name] = {}
        
        now = datetime.now(timezone.utc).isoformat()
        item.created_at = item.created_at or now
        item.updated_at = now
        
        key = f"{item.pk}#{item.sk}"
        self._storage[table_name][key] = item
        return True
    
    async def get_item(self, table_type: DynamoDBTableType, pk: str, sk: str | None = None) -> DynamoDBItem | None:
        table_name = self._get_table_name(table_type)
        if table_name not in self._storage:
            return None
        
        key = f"{pk}#{sk or ''}"
        return self._storage[table_name].get(key)
    
    async def delete_item(self, table_type: DynamoDBTableType, pk: str, sk: str | None = None) -> bool:
        table_name = self._get_table_name(table_type)
        if table_name not in self._storage:
            return True
        
        key = f"{pk}#{sk or ''}"
        self._storage[table_name].pop(key, None)
        return True
    
    async def query(
        self,
        table_type: DynamoDBTableType,
        pk: str,
        sk_prefix: str | None = None,
        limit: int = 100,
        scan_forward: bool = True,
    ) -> list[DynamoDBItem]:
        table_name = self._get_table_name(table_type)
        if table_name not in self._storage:
            return []
        
        items = []
        for key, item in self._storage[table_name].items():
            if item.pk == pk:
                if sk_prefix is None or item.sk.startswith(sk_prefix):
                    items.append(item)
        
        items.sort(key=lambda x: x.sk, reverse=not scan_forward)
        return items[:limit]


# =============================================================================
# Client Initialization
# =============================================================================

async def init_dynamodb(settings) -> DynamoDBClient:
    """Initialize DynamoDB client based on settings."""
    global _dynamodb_client
    
    if hasattr(settings, 'dynamodb'):
        client = DynamoDBClient(
            region=settings.dynamodb.region,
            endpoint_url=settings.dynamodb.endpoint_url,
            table_prefix=settings.dynamodb.table_prefix,
        )
    else:
        # Use mock client if no DynamoDB settings
        client = MockDynamoDBClient()
    
    connected = await client.connect()
    
    if not connected:
        logger.warning("Using mock DynamoDB client")
        client = MockDynamoDBClient()
        await client.connect()
    
    # Create tables
    await client.create_tables()
    
    _dynamodb_client = client
    return client


def get_dynamodb_client() -> DynamoDBClient:
    """Get the initialized DynamoDB client."""
    if _dynamodb_client is None:
        # Return mock client if not initialized
        return MockDynamoDBClient()
    return _dynamodb_client
