"""
Vector Store (OpenSearch) Backup Operations

Supports:
- Index snapshots
- S3 repository management
- Index export/import
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import asyncio
import json
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class VectorBackupConfig:
    """Configuration for vector store backup."""
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    user: str = "admin"
    password: str = "admin"
    backup_dir: str = "./backups/vector"
    # S3 settings for remote backup
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"


@dataclass
class VectorSnapshotInfo:
    """Information about a vector store snapshot."""
    snapshot_name: str
    repository: str
    state: str  # SUCCESS, IN_PROGRESS, PARTIAL, FAILED
    start_time: datetime | None = None
    end_time: datetime | None = None
    indices: list[str] = field(default_factory=list)
    shards: dict[str, int] = field(default_factory=dict)


@dataclass
class VectorBackupResult:
    """Result of a vector backup operation."""
    success: bool
    snapshot_name: str
    repository: str
    indices_backed_up: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class VectorBackup:
    """
    OpenSearch vector store backup and restore operations.
    
    Uses OpenSearch snapshot API for reliable backups.
    Supports both local filesystem and S3 repositories.
    """
    
    def __init__(self, config: VectorBackupConfig, client: Any = None):
        self.config = config
        self.client = client
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)
    
    async def _get_client(self):
        """Get OpenSearch client."""
        if self.client:
            return self.client
        
        try:
            from opensearchpy import AsyncOpenSearch
            
            auth = (self.config.user, self.config.password)
            client = AsyncOpenSearch(
                hosts=[{"host": self.config.host, "port": self.config.port}],
                http_auth=auth,
                use_ssl=self.config.use_ssl,
                verify_certs=False,
            )
            return client
        except ImportError:
            logger.error("opensearch-py not installed")
            return None
    
    async def create_fs_repository(
        self,
        repository_name: str = "aegis_backup",
    ) -> bool:
        """
        Create a filesystem-based snapshot repository.
        
        Note: The backup location must be registered in opensearch.yml
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            body = {
                "type": "fs",
                "settings": {
                    "location": self.config.backup_dir,
                    "compress": True,
                }
            }
            
            await client.snapshot.create_repository(
                repository=repository_name,
                body=body,
            )
            
            logger.info("Created filesystem repository", name=repository_name)
            return True
            
        except Exception as e:
            logger.error("Failed to create repository", error=str(e))
            return False
    
    async def create_s3_repository(
        self,
        repository_name: str = "aegis_s3_backup",
        base_path: str = "opensearch/snapshots",
    ) -> bool:
        """
        Create an S3-based snapshot repository.
        
        Requires S3 repository plugin installed in OpenSearch.
        """
        if not self.config.s3_bucket:
            logger.error("S3 bucket not configured")
            return False
        
        client = await self._get_client()
        if not client:
            return False
        
        try:
            body = {
                "type": "s3",
                "settings": {
                    "bucket": self.config.s3_bucket,
                    "region": self.config.s3_region,
                    "base_path": base_path,
                    "compress": True,
                }
            }
            
            await client.snapshot.create_repository(
                repository=repository_name,
                body=body,
            )
            
            logger.info("Created S3 repository", name=repository_name, bucket=self.config.s3_bucket)
            return True
            
        except Exception as e:
            logger.error("Failed to create S3 repository", error=str(e))
            return False
    
    async def create_snapshot(
        self,
        repository: str = "aegis_backup",
        snapshot_name: str | None = None,
        indices: list[str] | None = None,
        wait_for_completion: bool = True,
    ) -> VectorBackupResult:
        """
        Create a snapshot of indices.
        
        Args:
            repository: Repository name
            snapshot_name: Optional custom snapshot name
            indices: Optional list of indices (default: all)
            wait_for_completion: Wait for snapshot to complete
        
        Returns:
            VectorBackupResult
        """
        start_time = datetime.now(timezone.utc)
        
        if not snapshot_name:
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"snapshot_{timestamp}"
        
        result = VectorBackupResult(
            success=False,
            snapshot_name=snapshot_name,
            repository=repository,
        )
        
        client = await self._get_client()
        if not client:
            result.errors.append("OpenSearch client not available")
            return result
        
        try:
            body = {
                "ignore_unavailable": True,
                "include_global_state": False,
            }
            
            if indices:
                body["indices"] = ",".join(indices)
                result.indices_backed_up = indices
            
            logger.info(
                "Creating OpenSearch snapshot",
                snapshot=snapshot_name,
                indices=indices or "all",
            )
            
            response = await client.snapshot.create(
                repository=repository,
                snapshot=snapshot_name,
                body=body,
                wait_for_completion=wait_for_completion,
            )
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            snapshot_info = response.get("snapshot", {})
            if snapshot_info.get("state") == "SUCCESS":
                result.success = True
                result.indices_backed_up = snapshot_info.get("indices", [])
                logger.info(
                    "Snapshot created successfully",
                    snapshot=snapshot_name,
                    indices=len(result.indices_backed_up),
                )
            else:
                result.errors.append(f"Snapshot state: {snapshot_info.get('state')}")
                if "failures" in snapshot_info:
                    result.errors.extend([str(f) for f in snapshot_info["failures"]])
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Snapshot creation failed", error=str(e))
            return result
    
    async def restore_snapshot(
        self,
        repository: str,
        snapshot_name: str,
        indices: list[str] | None = None,
        rename_pattern: str | None = None,
        rename_replacement: str | None = None,
        wait_for_completion: bool = True,
    ) -> VectorBackupResult:
        """
        Restore from a snapshot.
        
        Args:
            repository: Repository name
            snapshot_name: Snapshot to restore
            indices: Optional specific indices to restore
            rename_pattern: Regex pattern for index renaming
            rename_replacement: Replacement string for renaming
            wait_for_completion: Wait for restore to complete
        
        Returns:
            VectorBackupResult
        """
        start_time = datetime.now(timezone.utc)
        
        result = VectorBackupResult(
            success=False,
            snapshot_name=snapshot_name,
            repository=repository,
        )
        
        client = await self._get_client()
        if not client:
            result.errors.append("OpenSearch client not available")
            return result
        
        try:
            body = {
                "ignore_unavailable": True,
                "include_global_state": False,
            }
            
            if indices:
                body["indices"] = ",".join(indices)
            
            if rename_pattern and rename_replacement:
                body["rename_pattern"] = rename_pattern
                body["rename_replacement"] = rename_replacement
            
            logger.info(
                "Restoring OpenSearch snapshot",
                snapshot=snapshot_name,
                indices=indices or "all",
            )
            
            response = await client.snapshot.restore(
                repository=repository,
                snapshot=snapshot_name,
                body=body,
                wait_for_completion=wait_for_completion,
            )
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            # Check restore status
            restore_info = response.get("snapshot", {})
            shards = restore_info.get("shards", {})
            
            if shards.get("failed", 0) == 0:
                result.success = True
                result.indices_backed_up = restore_info.get("indices", [])
                logger.info(
                    "Snapshot restored successfully",
                    snapshot=snapshot_name,
                    indices=len(result.indices_backed_up),
                )
            else:
                result.errors.append(f"Failed shards: {shards.get('failed')}")
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Snapshot restore failed", error=str(e))
            return result
    
    async def list_snapshots(
        self,
        repository: str = "aegis_backup",
    ) -> list[VectorSnapshotInfo]:
        """List all snapshots in a repository."""
        client = await self._get_client()
        if not client:
            return []
        
        try:
            response = await client.snapshot.get(
                repository=repository,
                snapshot="_all",
            )
            
            snapshots = []
            for snap in response.get("snapshots", []):
                info = VectorSnapshotInfo(
                    snapshot_name=snap["snapshot"],
                    repository=repository,
                    state=snap["state"],
                    indices=snap.get("indices", []),
                    shards=snap.get("shards", {}),
                )
                
                if "start_time" in snap:
                    info.start_time = datetime.fromisoformat(
                        snap["start_time"].replace("Z", "+00:00")
                    )
                if "end_time" in snap:
                    info.end_time = datetime.fromisoformat(
                        snap["end_time"].replace("Z", "+00:00")
                    )
                
                snapshots.append(info)
            
            # Sort by start time (newest first)
            snapshots.sort(
                key=lambda x: x.start_time or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            
            return snapshots
            
        except Exception as e:
            logger.error("Failed to list snapshots", error=str(e))
            return []
    
    async def delete_snapshot(
        self,
        repository: str,
        snapshot_name: str,
    ) -> bool:
        """Delete a snapshot."""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            await client.snapshot.delete(
                repository=repository,
                snapshot=snapshot_name,
            )
            
            logger.info("Deleted snapshot", snapshot=snapshot_name)
            return True
            
        except Exception as e:
            logger.error("Failed to delete snapshot", error=str(e))
            return False
    
    async def get_snapshot_status(
        self,
        repository: str,
        snapshot_name: str,
    ) -> VectorSnapshotInfo | None:
        """Get status of a specific snapshot."""
        client = await self._get_client()
        if not client:
            return None
        
        try:
            response = await client.snapshot.status(
                repository=repository,
                snapshot=snapshot_name,
            )
            
            snapshots = response.get("snapshots", [])
            if not snapshots:
                return None
            
            snap = snapshots[0]
            return VectorSnapshotInfo(
                snapshot_name=snap["snapshot"],
                repository=repository,
                state=snap["state"],
                indices=list(snap.get("indices", {}).keys()),
                shards=snap.get("shards_stats", {}),
            )
            
        except Exception as e:
            logger.error("Failed to get snapshot status", error=str(e))
            return None
    
    async def export_index_to_json(
        self,
        index_name: str,
        output_file: str | None = None,
        batch_size: int = 1000,
    ) -> tuple[bool, str, int]:
        """
        Export an index to JSON file (for small indices).
        
        Args:
            index_name: Index to export
            output_file: Output file path
            batch_size: Documents per batch
        
        Returns:
            Tuple of (success, file_path, doc_count)
        """
        client = await self._get_client()
        if not client:
            return False, "", 0
        
        if not output_file:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = str(Path(self.config.backup_dir) / f"{index_name}_{timestamp}.json")
        
        try:
            logger.info("Exporting index to JSON", index=index_name)
            
            # Get all documents using scroll
            documents = []
            response = await client.search(
                index=index_name,
                body={"query": {"match_all": {}}, "size": batch_size},
                scroll="5m",
            )
            
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            
            while hits:
                documents.extend([
                    {"_id": hit["_id"], "_source": hit["_source"]}
                    for hit in hits
                ])
                
                response = await client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = response["_scroll_id"]
                hits = response["hits"]["hits"]
            
            # Clear scroll
            await client.clear_scroll(scroll_id=scroll_id)
            
            # Write to file
            export_data = {
                "index": index_name,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "document_count": len(documents),
                "documents": documents,
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(
                "Index exported to JSON",
                index=index_name,
                documents=len(documents),
                file=output_file,
            )
            
            return True, output_file, len(documents)
            
        except Exception as e:
            logger.error("Index export failed", error=str(e))
            return False, "", 0
    
    async def import_index_from_json(
        self,
        input_file: str,
        target_index: str | None = None,
        batch_size: int = 500,
    ) -> tuple[bool, int]:
        """
        Import an index from JSON file.
        
        Args:
            input_file: JSON file to import
            target_index: Target index name (default: original)
            batch_size: Documents per bulk request
        
        Returns:
            Tuple of (success, doc_count)
        """
        client = await self._get_client()
        if not client:
            return False, 0
        
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            index_name = target_index or data["index"]
            documents = data["documents"]
            
            logger.info(
                "Importing index from JSON",
                file=input_file,
                index=index_name,
                documents=len(documents),
            )
            
            # Bulk import
            imported = 0
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                
                bulk_body = []
                for doc in batch:
                    bulk_body.append({"index": {"_index": index_name, "_id": doc["_id"]}})
                    bulk_body.append(doc["_source"])
                
                response = await client.bulk(body=bulk_body)
                
                if not response.get("errors"):
                    imported += len(batch)
                else:
                    # Count successful items
                    for item in response.get("items", []):
                        if "error" not in item.get("index", {}):
                            imported += 1
            
            logger.info("Index import completed", imported=imported)
            return True, imported
            
        except Exception as e:
            logger.error("Index import failed", error=str(e))
            return False, 0
    
    async def cleanup_old_snapshots(
        self,
        repository: str,
        keep_count: int = 5,
    ) -> int:
        """
        Delete old snapshots, keeping the most recent ones.
        
        Args:
            repository: Repository name
            keep_count: Number of recent snapshots to keep
        
        Returns:
            Number of snapshots deleted
        """
        snapshots = await self.list_snapshots(repository)
        
        if len(snapshots) <= keep_count:
            return 0
        
        deleted = 0
        for snapshot in snapshots[keep_count:]:
            if await self.delete_snapshot(repository, snapshot.snapshot_name):
                deleted += 1
        
        logger.info("Cleaned up old snapshots", deleted=deleted)
        return deleted
