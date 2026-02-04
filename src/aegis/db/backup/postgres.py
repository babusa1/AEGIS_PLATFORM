"""
PostgreSQL/TimescaleDB Backup Operations

Supports:
- pg_dump/pg_restore for full backups
- Table-level backups
- TimescaleDB-specific backup operations
- S3 upload for cloud storage
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import asyncio
import gzip
import os
import shutil
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PostgresBackupConfig:
    """Configuration for PostgreSQL backup."""
    host: str = "localhost"
    port: int = 5432
    user: str = "aegis"
    password: str = ""
    database: str = "aegis"
    backup_dir: str = "./backups/postgres"
    compress: bool = True
    include_timescale: bool = True


@dataclass
class PostgresRestoreResult:
    """Result of a restore operation."""
    success: bool
    backup_file: str
    restored_at: datetime
    tables_restored: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class PostgresBackup:
    """
    PostgreSQL/TimescaleDB backup operations.
    
    Uses pg_dump and pg_restore for reliable backups.
    Supports both local file storage and S3 upload.
    """
    
    def __init__(self, config: PostgresBackupConfig):
        self.config = config
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_env(self) -> dict:
        """Get environment variables for pg commands."""
        env = os.environ.copy()
        env["PGPASSWORD"] = self.config.password
        return env
    
    def _generate_backup_filename(
        self,
        prefix: str = "aegis",
        suffix: str = "",
    ) -> str:
        """Generate a timestamped backup filename."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ext = ".sql.gz" if self.config.compress else ".sql"
        return f"{prefix}_{timestamp}{suffix}{ext}"
    
    async def full_backup(
        self,
        custom_filename: str | None = None,
    ) -> tuple[bool, str]:
        """
        Perform a full database backup using pg_dump.
        
        Args:
            custom_filename: Optional custom filename for backup
        
        Returns:
            Tuple of (success, backup_file_path)
        """
        filename = custom_filename or self._generate_backup_filename("full")
        backup_path = Path(self.config.backup_dir) / filename
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", self.config.host,
            "-p", str(self.config.port),
            "-U", self.config.user,
            "-d", self.config.database,
            "-F", "p",  # Plain SQL format
            "--no-owner",
            "--no-acl",
        ]
        
        # Add TimescaleDB pre-restore options if needed
        if self.config.include_timescale:
            cmd.extend([
                "--no-tablespaces",
            ])
        
        try:
            logger.info("Starting PostgreSQL full backup", database=self.config.database)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(),
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("pg_dump failed", stderr=stderr.decode())
                return False, ""
            
            # Write output (compress if configured)
            if self.config.compress:
                with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                    f.write(stdout.decode())
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(stdout.decode())
            
            file_size = backup_path.stat().st_size
            logger.info(
                "PostgreSQL backup completed",
                file=str(backup_path),
                size_mb=round(file_size / 1024 / 1024, 2),
            )
            
            return True, str(backup_path)
            
        except Exception as e:
            logger.error("PostgreSQL backup failed", error=str(e))
            return False, ""
    
    async def table_backup(
        self,
        tables: list[str],
        custom_filename: str | None = None,
    ) -> tuple[bool, str]:
        """
        Backup specific tables.
        
        Args:
            tables: List of table names to backup
            custom_filename: Optional custom filename
        
        Returns:
            Tuple of (success, backup_file_path)
        """
        suffix = f"_tables_{len(tables)}"
        filename = custom_filename or self._generate_backup_filename("partial", suffix)
        backup_path = Path(self.config.backup_dir) / filename
        
        # Build pg_dump command with table specifications
        cmd = [
            "pg_dump",
            "-h", self.config.host,
            "-p", str(self.config.port),
            "-U", self.config.user,
            "-d", self.config.database,
            "-F", "p",
            "--no-owner",
            "--no-acl",
        ]
        
        for table in tables:
            cmd.extend(["-t", table])
        
        try:
            logger.info("Starting table backup", tables=tables)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(),
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("Table backup failed", stderr=stderr.decode())
                return False, ""
            
            if self.config.compress:
                with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                    f.write(stdout.decode())
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(stdout.decode())
            
            logger.info("Table backup completed", file=str(backup_path))
            return True, str(backup_path)
            
        except Exception as e:
            logger.error("Table backup failed", error=str(e))
            return False, ""
    
    async def schema_backup(
        self,
        custom_filename: str | None = None,
    ) -> tuple[bool, str]:
        """
        Backup only the schema (no data).
        
        Returns:
            Tuple of (success, backup_file_path)
        """
        filename = custom_filename or self._generate_backup_filename("schema")
        backup_path = Path(self.config.backup_dir) / filename
        
        cmd = [
            "pg_dump",
            "-h", self.config.host,
            "-p", str(self.config.port),
            "-U", self.config.user,
            "-d", self.config.database,
            "-F", "p",
            "--schema-only",
            "--no-owner",
            "--no-acl",
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(),
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return False, ""
            
            if self.config.compress:
                with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                    f.write(stdout.decode())
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(stdout.decode())
            
            return True, str(backup_path)
            
        except Exception as e:
            logger.error("Schema backup failed", error=str(e))
            return False, ""
    
    async def restore(
        self,
        backup_file: str,
        drop_existing: bool = False,
    ) -> PostgresRestoreResult:
        """
        Restore from a backup file.
        
        Args:
            backup_file: Path to backup file
            drop_existing: Whether to drop existing objects
        
        Returns:
            PostgresRestoreResult with details
        """
        start_time = datetime.now(timezone.utc)
        result = PostgresRestoreResult(
            success=False,
            backup_file=backup_file,
            restored_at=start_time,
        )
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            result.errors.append(f"Backup file not found: {backup_file}")
            return result
        
        try:
            # Read backup content
            if backup_file.endswith(".gz"):
                with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                    sql_content = f.read()
            else:
                with open(backup_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
            
            # Prepare restore command
            cmd = [
                "psql",
                "-h", self.config.host,
                "-p", str(self.config.port),
                "-U", self.config.user,
                "-d", self.config.database,
                "-v", "ON_ERROR_STOP=1",
            ]
            
            logger.info("Starting PostgreSQL restore", file=backup_file)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(),
            )
            
            stdout, stderr = await process.communicate(input=sql_content.encode())
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            if process.returncode != 0:
                result.errors.append(stderr.decode())
                logger.error("Restore failed", stderr=stderr.decode())
                return result
            
            result.success = True
            logger.info(
                "PostgreSQL restore completed",
                duration_seconds=result.duration_seconds,
            )
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Restore failed", error=str(e))
            return result
    
    async def list_backups(self) -> list[dict]:
        """List all available backups."""
        backups = []
        backup_dir = Path(self.config.backup_dir)
        
        for file in backup_dir.glob("*.sql*"):
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "path": str(file),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "compressed": file.suffix == ".gz",
            })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    async def cleanup_old_backups(
        self,
        keep_count: int = 10,
        keep_days: int | None = None,
    ) -> int:
        """
        Clean up old backup files.
        
        Args:
            keep_count: Number of recent backups to keep
            keep_days: Alternatively, keep backups from last N days
        
        Returns:
            Number of files deleted
        """
        backups = await self.list_backups()
        deleted = 0
        
        if keep_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
            for backup in backups:
                if backup["created_at"] < cutoff:
                    try:
                        os.remove(backup["path"])
                        deleted += 1
                        logger.debug("Deleted old backup", file=backup["filename"])
                    except Exception as e:
                        logger.error("Failed to delete backup", file=backup["filename"], error=str(e))
        else:
            # Keep only the most recent keep_count backups
            for backup in backups[keep_count:]:
                try:
                    os.remove(backup["path"])
                    deleted += 1
                except Exception as e:
                    logger.error("Failed to delete backup", file=backup["filename"], error=str(e))
        
        if deleted > 0:
            logger.info("Cleaned up old backups", deleted=deleted)
        
        return deleted
    
    async def upload_to_s3(
        self,
        backup_file: str,
        bucket: str,
        key_prefix: str = "backups/postgres/",
    ) -> tuple[bool, str]:
        """
        Upload backup to S3.
        
        Args:
            backup_file: Local backup file path
            bucket: S3 bucket name
            key_prefix: S3 key prefix
        
        Returns:
            Tuple of (success, s3_uri)
        """
        try:
            import aioboto3
            
            backup_path = Path(backup_file)
            s3_key = f"{key_prefix}{backup_path.name}"
            
            session = aioboto3.Session()
            async with session.client("s3") as s3:
                await s3.upload_file(str(backup_path), bucket, s3_key)
            
            s3_uri = f"s3://{bucket}/{s3_key}"
            logger.info("Uploaded backup to S3", uri=s3_uri)
            return True, s3_uri
            
        except ImportError:
            logger.error("aioboto3 not installed")
            return False, ""
        except Exception as e:
            logger.error("S3 upload failed", error=str(e))
            return False, ""


# Import timedelta for cleanup
from datetime import timedelta
