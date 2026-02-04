"""
AEGIS Database Clients Module

Centralized database connection management.
"""
from aegis.db.clients import (
    DatabaseClients,
    get_db_clients,
    init_db_clients,
    close_db_clients,
    init_dynamodb,
)
from aegis.db.dynamodb import (
    DynamoDBClient,
    DynamoDBItem,
    DynamoDBTableType,
    MockDynamoDBClient,
    get_dynamodb_client,
)
from aegis.db.timescale import (
    TimescaleDBClient,
    TimeInterval,
    GapFillMethod,
    TimeSeriesPoint,
    AggregatedPoint,
    VitalSign,
    get_timescale_client,
)
from aegis.db.backup import (
    BackupManager,
    BackupTarget,
    BackupResult,
    BackupSchedule,
    PostgresBackup,
    GraphBackup,
    VectorBackup,
    get_backup_manager,
)

__all__ = [
    # Core clients
    "DatabaseClients",
    "get_db_clients",
    "init_db_clients",
    "close_db_clients",
    # DynamoDB
    "DynamoDBClient",
    "DynamoDBItem",
    "DynamoDBTableType",
    "MockDynamoDBClient",
    "get_dynamodb_client",
    "init_dynamodb",
    # TimescaleDB
    "TimescaleDBClient",
    "TimeInterval",
    "GapFillMethod",
    "TimeSeriesPoint",
    "AggregatedPoint",
    "VitalSign",
    "get_timescale_client",
    # Backup
    "BackupManager",
    "BackupTarget",
    "BackupResult",
    "BackupSchedule",
    "PostgresBackup",
    "GraphBackup",
    "VectorBackup",
    "get_backup_manager",
]
