"""
AEGIS Database Backup Utilities

Unified backup/restore operations for all data stores:
- PostgreSQL/TimescaleDB
- JanusGraph (Neptune-compatible)
- OpenSearch (Vector DB)
"""
from .postgres import PostgresBackup, PostgresRestoreResult
from .graph import GraphBackup, GraphExportFormat
from .vector import VectorBackup, VectorSnapshotInfo
from .manager import (
    BackupManager,
    BackupTarget,
    BackupResult,
    BackupSchedule,
    get_backup_manager,
)

__all__ = [
    # Postgres
    "PostgresBackup",
    "PostgresRestoreResult",
    # Graph
    "GraphBackup",
    "GraphExportFormat",
    # Vector
    "VectorBackup",
    "VectorSnapshotInfo",
    # Manager
    "BackupManager",
    "BackupTarget",
    "BackupResult",
    "BackupSchedule",
    "get_backup_manager",
]
