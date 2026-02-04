"""
AEGIS Unified Backup Manager

Coordinates backups across all data stores with scheduling support.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal
from enum import Enum
import asyncio
import structlog

from .postgres import PostgresBackup, PostgresBackupConfig
from .graph import GraphBackup, GraphBackupConfig, GraphExportFormat
from .vector import VectorBackup, VectorBackupConfig

logger = structlog.get_logger(__name__)

# Global manager instance
_backup_manager: "BackupManager | None" = None


class BackupTarget(str, Enum):
    """Available backup targets."""
    POSTGRES = "postgres"
    GRAPH = "graph"
    VECTOR = "vector"
    ALL = "all"


@dataclass
class BackupResult:
    """Result of a backup operation."""
    target: BackupTarget
    success: bool
    started_at: datetime
    completed_at: datetime | None = None
    file_path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class BackupSchedule:
    """Backup schedule configuration."""
    target: BackupTarget
    cron: str  # Cron expression
    enabled: bool = True
    retention_days: int = 30
    upload_to_s3: bool = False
    s3_bucket: str | None = None


@dataclass
class BackupManagerConfig:
    """Configuration for backup manager."""
    postgres: PostgresBackupConfig | None = None
    graph: GraphBackupConfig | None = None
    vector: VectorBackupConfig | None = None
    schedules: list[BackupSchedule] = field(default_factory=list)


class BackupManager:
    """
    Unified backup manager for AEGIS data stores.
    
    Coordinates backups across:
    - PostgreSQL/TimescaleDB
    - JanusGraph
    - OpenSearch
    
    Features:
    - Manual and scheduled backups
    - Cross-store consistency
    - Progress tracking
    - Error handling and retries
    """
    
    def __init__(
        self,
        config: BackupManagerConfig,
        postgres_pool: Any = None,
        graph_client: Any = None,
        opensearch_client: Any = None,
    ):
        self.config = config
        
        # Initialize individual backup handlers
        self._postgres: PostgresBackup | None = None
        self._graph: GraphBackup | None = None
        self._vector: VectorBackup | None = None
        
        if config.postgres:
            self._postgres = PostgresBackup(config.postgres)
        
        if config.graph:
            self._graph = GraphBackup(config.graph, graph_client)
        
        if config.vector:
            self._vector = VectorBackup(config.vector, opensearch_client)
        
        # Backup history
        self._history: list[BackupResult] = []
        self._running: dict[BackupTarget, bool] = {}
        
        # Callbacks
        self._on_complete: list[Callable[[BackupResult], None]] = []
    
    def on_backup_complete(self, callback: Callable[[BackupResult], None]):
        """Register a callback for backup completion."""
        self._on_complete.append(callback)
    
    async def backup_postgres(
        self,
        tables: list[str] | None = None,
        upload_s3: bool = False,
        s3_bucket: str | None = None,
    ) -> BackupResult:
        """
        Backup PostgreSQL database.
        
        Args:
            tables: Optional specific tables (default: full backup)
            upload_s3: Whether to upload to S3
            s3_bucket: S3 bucket name
        
        Returns:
            BackupResult
        """
        result = BackupResult(
            target=BackupTarget.POSTGRES,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._postgres:
            result.errors.append("PostgreSQL backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        if self._running.get(BackupTarget.POSTGRES):
            result.errors.append("PostgreSQL backup already in progress")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        self._running[BackupTarget.POSTGRES] = True
        
        try:
            logger.info("Starting PostgreSQL backup", tables=tables or "all")
            
            if tables:
                success, file_path = await self._postgres.table_backup(tables)
            else:
                success, file_path = await self._postgres.full_backup()
            
            result.success = success
            result.file_path = file_path
            
            # Upload to S3 if requested
            if success and upload_s3 and s3_bucket:
                s3_success, s3_uri = await self._postgres.upload_to_s3(
                    file_path,
                    s3_bucket,
                )
                result.details["s3_uri"] = s3_uri if s3_success else None
                result.details["s3_upload"] = s3_success
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("PostgreSQL backup failed", error=str(e))
        finally:
            self._running[BackupTarget.POSTGRES] = False
            result.completed_at = datetime.now(timezone.utc)
            self._history.append(result)
            self._notify_complete(result)
        
        return result
    
    async def backup_graph(
        self,
        format: GraphExportFormat = GraphExportFormat.JSON,
        vertex_labels: list[str] | None = None,
    ) -> BackupResult:
        """
        Backup graph database.
        
        Args:
            format: Export format
            vertex_labels: Optional specific vertex labels
        
        Returns:
            BackupResult
        """
        result = BackupResult(
            target=BackupTarget.GRAPH,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._graph:
            result.errors.append("Graph backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        if self._running.get(BackupTarget.GRAPH):
            result.errors.append("Graph backup already in progress")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        self._running[BackupTarget.GRAPH] = True
        
        try:
            logger.info("Starting graph backup", format=format.value)
            
            if format == GraphExportFormat.JSON:
                graph_result = await self._graph.export_to_json(
                    vertex_labels=vertex_labels
                )
            elif format == GraphExportFormat.GREMLIN:
                graph_result = await self._graph.export_to_gremlin()
            else:
                result.errors.append(f"Unsupported format: {format}")
                result.completed_at = datetime.now(timezone.utc)
                return result
            
            result.success = graph_result.success
            result.file_path = graph_result.file_path
            result.details = {
                "format": format.value,
                "vertex_count": graph_result.vertex_count,
                "edge_count": graph_result.edge_count,
            }
            result.errors.extend(graph_result.errors)
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Graph backup failed", error=str(e))
        finally:
            self._running[BackupTarget.GRAPH] = False
            result.completed_at = datetime.now(timezone.utc)
            self._history.append(result)
            self._notify_complete(result)
        
        return result
    
    async def backup_vector(
        self,
        repository: str = "aegis_backup",
        indices: list[str] | None = None,
    ) -> BackupResult:
        """
        Backup vector store (OpenSearch).
        
        Args:
            repository: Snapshot repository name
            indices: Optional specific indices
        
        Returns:
            BackupResult
        """
        result = BackupResult(
            target=BackupTarget.VECTOR,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._vector:
            result.errors.append("Vector backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        if self._running.get(BackupTarget.VECTOR):
            result.errors.append("Vector backup already in progress")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        self._running[BackupTarget.VECTOR] = True
        
        try:
            logger.info("Starting vector store backup", indices=indices or "all")
            
            vector_result = await self._vector.create_snapshot(
                repository=repository,
                indices=indices,
            )
            
            result.success = vector_result.success
            result.file_path = f"{repository}/{vector_result.snapshot_name}"
            result.details = {
                "repository": repository,
                "snapshot_name": vector_result.snapshot_name,
                "indices": vector_result.indices_backed_up,
            }
            result.errors.extend(vector_result.errors)
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Vector backup failed", error=str(e))
        finally:
            self._running[BackupTarget.VECTOR] = False
            result.completed_at = datetime.now(timezone.utc)
            self._history.append(result)
            self._notify_complete(result)
        
        return result
    
    async def backup_all(
        self,
        upload_s3: bool = False,
        s3_bucket: str | None = None,
    ) -> list[BackupResult]:
        """
        Backup all configured data stores.
        
        Runs backups in parallel where possible.
        
        Returns:
            List of BackupResults
        """
        logger.info("Starting full backup of all data stores")
        
        tasks = []
        
        if self._postgres:
            tasks.append(self.backup_postgres(upload_s3=upload_s3, s3_bucket=s3_bucket))
        
        if self._graph:
            tasks.append(self.backup_graph())
        
        if self._vector:
            tasks.append(self.backup_vector())
        
        if not tasks:
            logger.warning("No backup targets configured")
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = BackupResult(
                    target=BackupTarget.ALL,
                    success=False,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    errors=[str(result)],
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        # Summary
        success_count = sum(1 for r in final_results if r.success)
        logger.info(
            "Full backup completed",
            success=success_count,
            total=len(final_results),
        )
        
        return final_results
    
    async def restore_postgres(
        self,
        backup_file: str,
        drop_existing: bool = False,
    ) -> BackupResult:
        """Restore PostgreSQL from backup."""
        result = BackupResult(
            target=BackupTarget.POSTGRES,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._postgres:
            result.errors.append("PostgreSQL backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        try:
            restore_result = await self._postgres.restore(
                backup_file,
                drop_existing=drop_existing,
            )
            
            result.success = restore_result.success
            result.file_path = backup_file
            result.details = {
                "tables_restored": restore_result.tables_restored,
            }
            result.errors.extend(restore_result.errors)
            
        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    async def restore_graph(
        self,
        backup_file: str,
        clear_existing: bool = False,
    ) -> BackupResult:
        """Restore graph database from backup."""
        result = BackupResult(
            target=BackupTarget.GRAPH,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._graph:
            result.errors.append("Graph backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        try:
            graph_result = await self._graph.import_from_json(
                backup_file,
                clear_existing=clear_existing,
            )
            
            result.success = graph_result.success
            result.file_path = backup_file
            result.details = {
                "vertex_count": graph_result.vertex_count,
                "edge_count": graph_result.edge_count,
            }
            result.errors.extend(graph_result.errors)
            
        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    async def restore_vector(
        self,
        repository: str,
        snapshot_name: str,
        indices: list[str] | None = None,
    ) -> BackupResult:
        """Restore vector store from snapshot."""
        result = BackupResult(
            target=BackupTarget.VECTOR,
            success=False,
            started_at=datetime.now(timezone.utc),
        )
        
        if not self._vector:
            result.errors.append("Vector backup not configured")
            result.completed_at = datetime.now(timezone.utc)
            return result
        
        try:
            vector_result = await self._vector.restore_snapshot(
                repository=repository,
                snapshot_name=snapshot_name,
                indices=indices,
            )
            
            result.success = vector_result.success
            result.file_path = f"{repository}/{snapshot_name}"
            result.details = {
                "indices_restored": vector_result.indices_backed_up,
            }
            result.errors.extend(vector_result.errors)
            
        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    async def list_backups(
        self,
        target: BackupTarget | None = None,
    ) -> dict[str, list[dict]]:
        """
        List all available backups.
        
        Args:
            target: Optional filter by target
        
        Returns:
            Dict of target -> list of backups
        """
        result = {}
        
        if (target is None or target in [BackupTarget.POSTGRES, BackupTarget.ALL]) and self._postgres:
            result["postgres"] = await self._postgres.list_backups()
        
        if (target is None or target in [BackupTarget.GRAPH, BackupTarget.ALL]) and self._graph:
            result["graph"] = await self._graph.list_backups()
        
        if (target is None or target in [BackupTarget.VECTOR, BackupTarget.ALL]) and self._vector:
            snapshots = await self._vector.list_snapshots()
            result["vector"] = [
                {
                    "snapshot_name": s.snapshot_name,
                    "state": s.state,
                    "start_time": s.start_time,
                    "indices": s.indices,
                }
                for s in snapshots
            ]
        
        return result
    
    async def cleanup_old_backups(
        self,
        target: BackupTarget = BackupTarget.ALL,
        keep_count: int = 10,
    ) -> dict[str, int]:
        """
        Clean up old backups.
        
        Returns:
            Dict of target -> deleted count
        """
        deleted = {}
        
        if target in [BackupTarget.POSTGRES, BackupTarget.ALL] and self._postgres:
            deleted["postgres"] = await self._postgres.cleanup_old_backups(keep_count)
        
        # Graph backups are files, similar cleanup pattern
        if target in [BackupTarget.GRAPH, BackupTarget.ALL] and self._graph:
            # TODO: Implement graph backup cleanup
            deleted["graph"] = 0
        
        if target in [BackupTarget.VECTOR, BackupTarget.ALL] and self._vector:
            deleted["vector"] = await self._vector.cleanup_old_snapshots(
                "aegis_backup",
                keep_count,
            )
        
        return deleted
    
    def get_history(
        self,
        limit: int = 50,
        target: BackupTarget | None = None,
    ) -> list[BackupResult]:
        """Get backup history."""
        history = self._history
        
        if target:
            history = [r for r in history if r.target == target]
        
        return history[-limit:]
    
    def is_running(self, target: BackupTarget) -> bool:
        """Check if a backup is currently running."""
        if target == BackupTarget.ALL:
            return any(self._running.values())
        return self._running.get(target, False)
    
    def _notify_complete(self, result: BackupResult):
        """Notify callbacks of backup completion."""
        for callback in self._on_complete:
            try:
                callback(result)
            except Exception as e:
                logger.error("Backup callback failed", error=str(e))


def get_backup_manager() -> BackupManager | None:
    """Get the global backup manager instance."""
    return _backup_manager


async def init_backup_manager(
    config: BackupManagerConfig,
    postgres_pool: Any = None,
    graph_client: Any = None,
    opensearch_client: Any = None,
) -> BackupManager:
    """Initialize the global backup manager."""
    global _backup_manager
    
    _backup_manager = BackupManager(
        config=config,
        postgres_pool=postgres_pool,
        graph_client=graph_client,
        opensearch_client=opensearch_client,
    )
    
    logger.info("Backup manager initialized")
    return _backup_manager
