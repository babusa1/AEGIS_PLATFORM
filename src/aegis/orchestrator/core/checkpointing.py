"""
Durable Execution - Checkpointing and Replay

Enhanced checkpointing system with database persistence and replay capabilities.
Implements Temporal-style durable execution for workflows.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
import json
import hashlib
import structlog

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class CheckpointRecord(BaseModel):
    """Checkpoint record for database storage."""
    
    id: str
    execution_id: str
    workflow_id: str
    tenant_id: str
    
    # State snapshot
    state: Dict[str, Any]
    state_hash: str
    
    # Position
    node_id: Optional[str] = None
    step_number: int
    
    # Metadata
    created_at: datetime
    status: str = "active"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class CheckpointManager:
    """
    Manages workflow checkpoints with database persistence.
    
    Features:
    - Automatic checkpointing after each node
    - Manual checkpoint creation
    - Checkpoint restore/replay
    - Checkpoint cleanup policies
    - State integrity verification
    """
    
    def __init__(self, pool=None, tenant_id: str = "default"):
        self.pool = pool
        self.tenant_id = tenant_id
    
    async def create_checkpoint(
        self,
        execution_id: str,
        workflow_id: str,
        state: Dict[str, Any],
        node_id: Optional[str] = None,
        step_number: int = 0,
    ) -> CheckpointRecord:
        """
        Create and persist a checkpoint.
        
        Args:
            execution_id: Workflow execution ID
            workflow_id: Workflow definition ID
            state: Current workflow state
            node_id: Current node ID
            step_number: Step number in execution
            
        Returns:
            CheckpointRecord
        """
        # Calculate state hash for integrity
        state_json = json.dumps(state, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]
        
        checkpoint = CheckpointRecord(
            id=f"checkpoint-{execution_id}-{step_number}-{int(datetime.utcnow().timestamp())}",
            execution_id=execution_id,
            workflow_id=workflow_id,
            tenant_id=self.tenant_id,
            state=state,
            state_hash=state_hash,
            node_id=node_id,
            step_number=step_number,
            created_at=datetime.utcnow(),
        )
        
        # Persist to database
        await self._save_checkpoint(checkpoint)
        
        logger.info(
            "Checkpoint created",
            checkpoint_id=checkpoint.id,
            execution_id=execution_id,
            step_number=step_number,
        )
        
        return checkpoint
    
    async def _save_checkpoint(self, checkpoint: CheckpointRecord):
        """Save checkpoint to database."""
        if not self.pool:
            logger.warning("No database pool available, checkpoint not persisted")
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Create table if not exists
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                        id VARCHAR(255) PRIMARY KEY,
                        execution_id VARCHAR(255) NOT NULL,
                        workflow_id VARCHAR(255) NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL,
                        state JSONB NOT NULL,
                        state_hash VARCHAR(64) NOT NULL,
                        node_id VARCHAR(255),
                        step_number INTEGER NOT NULL,
                        status VARCHAR(32) DEFAULT 'active',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_execution 
                    ON workflow_checkpoints(execution_id, step_number)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_workflow 
                    ON workflow_checkpoints(workflow_id, created_at DESC)
                """)
                
                # Insert checkpoint
                await conn.execute("""
                    INSERT INTO workflow_checkpoints 
                    (id, execution_id, workflow_id, tenant_id, state, state_hash, 
                     node_id, step_number, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    checkpoint.id,
                    checkpoint.execution_id,
                    checkpoint.workflow_id,
                    checkpoint.tenant_id,
                    json.dumps(checkpoint.state, default=str),
                    checkpoint.state_hash,
                    checkpoint.node_id,
                    checkpoint.step_number,
                    checkpoint.status,
                    checkpoint.created_at,
                )
                
        except Exception as e:
            logger.error("Failed to save checkpoint", error=str(e), checkpoint_id=checkpoint.id)
            raise
    
    async def get_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[CheckpointRecord]:
        """Get a checkpoint by ID."""
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM workflow_checkpoints 
                    WHERE id = $1 AND tenant_id = $2
                """, checkpoint_id, self.tenant_id)
                
                if not row:
                    return None
                
                return CheckpointRecord(
                    id=row["id"],
                    execution_id=row["execution_id"],
                    workflow_id=row["workflow_id"],
                    tenant_id=row["tenant_id"],
                    state=row["state"] if isinstance(row["state"], dict) else json.loads(row["state"]),
                    state_hash=row["state_hash"],
                    node_id=row["node_id"],
                    step_number=row["step_number"],
                    created_at=row["created_at"],
                    status=row["status"],
                )
        except Exception as e:
            logger.error("Failed to get checkpoint", error=str(e), checkpoint_id=checkpoint_id)
            return None
    
    async def list_checkpoints(
        self,
        execution_id: str,
        limit: int = 100,
    ) -> List[CheckpointRecord]:
        """List all checkpoints for an execution."""
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM workflow_checkpoints 
                    WHERE execution_id = $1 AND tenant_id = $2
                    ORDER BY step_number ASC
                    LIMIT $3
                """, execution_id, self.tenant_id, limit)
                
                checkpoints = []
                for row in rows:
                    checkpoints.append(CheckpointRecord(
                        id=row["id"],
                        execution_id=row["execution_id"],
                        workflow_id=row["workflow_id"],
                        tenant_id=row["tenant_id"],
                        state=row["state"] if isinstance(row["state"], dict) else json.loads(row["state"]),
                        state_hash=row["state_hash"],
                        node_id=row["node_id"],
                        step_number=row["step_number"],
                        created_at=row["created_at"],
                        status=row["status"],
                    ))
                
                return checkpoints
        except Exception as e:
            logger.error("Failed to list checkpoints", error=str(e), execution_id=execution_id)
            return []
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from a checkpoint.
        
        Returns:
            Restored state dict, or None if checkpoint not found
        """
        checkpoint = await self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return None
        
        # Verify state integrity
        state_json = json.dumps(checkpoint.state, sort_keys=True, default=str)
        computed_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]
        
        if computed_hash != checkpoint.state_hash:
            logger.error(
                "Checkpoint integrity check failed",
                checkpoint_id=checkpoint_id,
                expected=checkpoint.state_hash,
                computed=computed_hash,
            )
            return None
        
        logger.info(
            "Restored from checkpoint",
            checkpoint_id=checkpoint_id,
            execution_id=checkpoint.execution_id,
            step_number=checkpoint.step_number,
        )
        
        return checkpoint.state
    
    async def replay_execution(
        self,
        execution_id: str,
        from_step: int = 0,
    ) -> List[CheckpointRecord]:
        """
        Replay execution from a specific step.
        
        Returns:
            List of checkpoints from the replay point forward
        """
        checkpoints = await self.list_checkpoints(execution_id)
        
        # Filter to steps >= from_step
        replay_checkpoints = [c for c in checkpoints if c.step_number >= from_step]
        
        logger.info(
            "Replay execution",
            execution_id=execution_id,
            from_step=from_step,
            checkpoint_count=len(replay_checkpoints),
        )
        
        return replay_checkpoints
    
    async def cleanup_old_checkpoints(
        self,
        execution_id: Optional[str] = None,
        older_than_days: int = 30,
        keep_latest: int = 10,
    ):
        """
        Cleanup old checkpoints.
        
        Args:
            execution_id: If provided, cleanup only for this execution
            older_than_days: Delete checkpoints older than this
            keep_latest: Always keep this many latest checkpoints per execution
        """
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                if execution_id:
                    # Cleanup for specific execution
                    await conn.execute("""
                        DELETE FROM workflow_checkpoints
                        WHERE execution_id = $1 
                          AND tenant_id = $2
                          AND created_at < NOW() - INTERVAL '%s days'
                          AND id NOT IN (
                              SELECT id FROM workflow_checkpoints
                              WHERE execution_id = $1
                              ORDER BY step_number DESC
                              LIMIT $3
                          )
                    """ % older_than_days, execution_id, self.tenant_id, keep_latest)
                else:
                    # Cleanup all old checkpoints
                    await conn.execute("""
                        DELETE FROM workflow_checkpoints
                        WHERE tenant_id = $1
                          AND created_at < NOW() - INTERVAL '%s days'
                          AND id NOT IN (
                              SELECT id FROM (
                                  SELECT id, ROW_NUMBER() OVER (
                                      PARTITION BY execution_id 
                                      ORDER BY step_number DESC
                                  ) as rn
                                  FROM workflow_checkpoints
                                  WHERE tenant_id = $1
                              ) ranked
                              WHERE rn <= $2
                          )
                    """ % older_than_days, self.tenant_id, keep_latest)
                
                logger.info("Cleaned up old checkpoints", older_than_days=older_than_days)
        except Exception as e:
            logger.error("Failed to cleanup checkpoints", error=str(e))
