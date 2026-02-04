"""
State Manager

LangGraph-style state management with:
- Checkpointing for durability
- Time-travel debugging
- State versioning
- Memory namespaces
"""

from typing import Any, TypedDict, Annotated, Callable
from datetime import datetime
from enum import Enum
import json
import hashlib
import operator
import uuid

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# State Schema
# =============================================================================

class WorkflowState(TypedDict, total=False):
    """
    Base workflow state schema.
    
    All workflows inherit from this and can extend with custom fields.
    Uses Annotated types for merge strategies.
    """
    # Execution context
    execution_id: str
    workflow_id: str
    tenant_id: str
    user_id: str | None
    
    # Input/Output
    inputs: dict
    outputs: Annotated[dict, lambda x, y: {**x, **y}]  # Merge outputs
    
    # Flow control
    current_node: str | None
    execution_path: Annotated[list[str], operator.add]  # Append path
    
    # Messages (for agent conversations)
    messages: Annotated[list[dict], operator.add]  # Append messages
    
    # Reasoning trace
    reasoning: Annotated[list[str], operator.add]  # Append reasoning
    
    # Error handling
    error: str | None
    error_node: str | None
    retry_count: int
    
    # Metadata
    created_at: str
    updated_at: str
    version: int


class StateUpdate(BaseModel):
    """A partial state update."""
    fields: dict
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Checkpointing
# =============================================================================

class CheckpointStatus(str, Enum):
    """Checkpoint status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Checkpoint(BaseModel):
    """
    A snapshot of workflow state at a point in time.
    
    Enables:
    - Crash recovery
    - Time-travel debugging
    - State rollback
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    workflow_id: str
    
    # State snapshot
    state: dict
    state_hash: str  # For integrity verification
    
    # Position in workflow
    node_id: str | None
    step_number: int
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    
    # Parent checkpoint (for branching)
    parent_checkpoint_id: str | None = None
    
    @classmethod
    def from_state(cls, execution_id: str, workflow_id: str, state: dict, 
                   node_id: str = None, step_number: int = 0) -> "Checkpoint":
        """Create checkpoint from current state."""
        state_json = json.dumps(state, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]
        
        return cls(
            execution_id=execution_id,
            workflow_id=workflow_id,
            state=state,
            state_hash=state_hash,
            node_id=node_id,
            step_number=step_number,
        )


# =============================================================================
# State Manager
# =============================================================================

class StateManager:
    """
    Manages workflow state with checkpointing and versioning.
    
    Features:
    - Automatic checkpointing
    - State validation
    - Time-travel (rollback to any checkpoint)
    - State history
    - Memory namespaces per tenant
    """
    
    def __init__(self, pool=None, tenant_id: str = "default"):
        self.pool = pool
        self.tenant_id = tenant_id
        self._checkpoints: dict[str, list[Checkpoint]] = {}  # In-memory cache
        self._current_states: dict[str, dict] = {}
    
    def create_initial_state(
        self,
        execution_id: str,
        workflow_id: str,
        inputs: dict,
        user_id: str = None,
    ) -> WorkflowState:
        """Create initial workflow state."""
        now = datetime.utcnow().isoformat()
        
        state: WorkflowState = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "inputs": inputs,
            "outputs": {},
            "current_node": None,
            "execution_path": [],
            "messages": [],
            "reasoning": [],
            "error": None,
            "error_node": None,
            "retry_count": 0,
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }
        
        self._current_states[execution_id] = state
        
        # Create initial checkpoint
        checkpoint = Checkpoint.from_state(
            execution_id=execution_id,
            workflow_id=workflow_id,
            state=state,
            step_number=0,
        )
        self._save_checkpoint(checkpoint)
        
        logger.info(
            "Created initial state",
            execution_id=execution_id,
            workflow_id=workflow_id,
        )
        
        return state
    
    def update_state(
        self,
        execution_id: str,
        updates: dict,
        node_id: str = None,
        create_checkpoint: bool = True,
    ) -> dict:
        """
        Update workflow state with partial updates.
        
        Handles merge strategies based on Annotated types.
        """
        if execution_id not in self._current_states:
            raise ValueError(f"Unknown execution: {execution_id}")
        
        current = self._current_states[execution_id]
        
        # Apply updates with merge strategies
        for key, value in updates.items():
            if key in current:
                existing = current.get(key)
                
                # Check for merge annotation (simplified - in production use typing introspection)
                if key in ["outputs"] and isinstance(existing, dict) and isinstance(value, dict):
                    current[key] = {**existing, **value}
                elif key in ["execution_path", "messages", "reasoning"] and isinstance(existing, list):
                    if isinstance(value, list):
                        current[key] = existing + value
                    else:
                        current[key] = existing + [value]
                else:
                    current[key] = value
            else:
                current[key] = value
        
        # Update metadata
        current["updated_at"] = datetime.utcnow().isoformat()
        current["version"] = current.get("version", 0) + 1
        current["current_node"] = node_id
        
        # Create checkpoint if requested
        if create_checkpoint:
            checkpoints = self._checkpoints.get(execution_id, [])
            checkpoint = Checkpoint.from_state(
                execution_id=execution_id,
                workflow_id=current.get("workflow_id", ""),
                state=current.copy(),
                node_id=node_id,
                step_number=len(checkpoints),
            )
            self._save_checkpoint(checkpoint)
        
        return current
    
    def get_state(self, execution_id: str) -> dict | None:
        """Get current state for an execution."""
        return self._current_states.get(execution_id)
    
    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save checkpoint to storage."""
        execution_id = checkpoint.execution_id
        
        if execution_id not in self._checkpoints:
            self._checkpoints[execution_id] = []
        
        self._checkpoints[execution_id].append(checkpoint)
        
        # Persist to database if available
        if self.pool:
            # Would save to workflow_checkpoints table
            pass
        
        logger.debug(
            "Saved checkpoint",
            execution_id=execution_id,
            checkpoint_id=checkpoint.id,
            step=checkpoint.step_number,
        )
    
    def get_checkpoints(self, execution_id: str) -> list[Checkpoint]:
        """Get all checkpoints for an execution."""
        return self._checkpoints.get(execution_id, [])
    
    def rollback_to_checkpoint(self, execution_id: str, checkpoint_id: str) -> dict:
        """
        Roll back state to a previous checkpoint.
        
        Enables time-travel debugging.
        """
        checkpoints = self._checkpoints.get(execution_id, [])
        
        target = None
        for cp in checkpoints:
            if cp.id == checkpoint_id:
                target = cp
                break
        
        if not target:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        # Restore state
        self._current_states[execution_id] = target.state.copy()
        
        # Mark checkpoints after this as rolled back
        target_index = checkpoints.index(target)
        for cp in checkpoints[target_index + 1:]:
            cp.status = CheckpointStatus.ROLLED_BACK
        
        logger.info(
            "Rolled back to checkpoint",
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            step=target.step_number,
        )
        
        return target.state
    
    def get_state_history(self, execution_id: str) -> list[dict]:
        """
        Get state history for time-travel debugging.
        
        Returns list of {step, node_id, state_summary, timestamp}
        """
        checkpoints = self._checkpoints.get(execution_id, [])
        
        history = []
        for cp in checkpoints:
            history.append({
                "step": cp.step_number,
                "checkpoint_id": cp.id,
                "node_id": cp.node_id,
                "status": cp.status.value,
                "state_hash": cp.state_hash,
                "timestamp": cp.created_at.isoformat(),
                "outputs_keys": list(cp.state.get("outputs", {}).keys()),
            })
        
        return history
    
    async def persist_state(self, execution_id: str):
        """Persist current state to database."""
        if not self.pool:
            return
        
        state = self._current_states.get(execution_id)
        if not state:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_states (execution_id, state, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (execution_id) DO UPDATE SET state = $2, updated_at = NOW()
            """, execution_id, json.dumps(state, default=str))
    
    async def load_state(self, execution_id: str) -> dict | None:
        """Load state from database."""
        if not self.pool:
            return self._current_states.get(execution_id)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT state FROM workflow_states WHERE execution_id = $1
            """, execution_id)
        
        if row:
            state = row["state"]
            self._current_states[execution_id] = state
            return state
        
        return None
    
    def clear_state(self, execution_id: str):
        """Clear state and checkpoints for an execution."""
        self._current_states.pop(execution_id, None)
        self._checkpoints.pop(execution_id, None)


# =============================================================================
# State Validators
# =============================================================================

class StateValidator:
    """Validates state against schema."""
    
    @staticmethod
    def validate(state: dict, schema: type) -> tuple[bool, list[str]]:
        """
        Validate state against a TypedDict schema.
        
        Returns (is_valid, list of errors)
        """
        errors = []
        
        # Get required fields from TypedDict
        annotations = getattr(schema, "__annotations__", {})
        required = getattr(schema, "__required_keys__", set())
        
        for field in required:
            if field not in state:
                errors.append(f"Missing required field: {field}")
        
        for field, value in state.items():
            if field in annotations:
                expected_type = annotations[field]
                # Simplified type checking
                if not isinstance(value, (type(None), dict, list, str, int, float, bool)):
                    errors.append(f"Invalid type for {field}")
        
        return len(errors) == 0, errors
