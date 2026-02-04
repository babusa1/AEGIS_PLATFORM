"""
Execution Engine

Temporal-style durable execution with:
- Crash recovery
- Retry policies
- Circuit breakers
- Timeout handling
- Dead letter queues
"""

from typing import Any, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import json
import traceback

import structlog
from pydantic import BaseModel, Field

from aegis.orchestrator.core.state import StateManager, Checkpoint

logger = structlog.get_logger(__name__)


# =============================================================================
# Execution Models
# =============================================================================

class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # Human-in-loop waiting
    WAITING = "waiting"  # Waiting for external event
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class RetryPolicy(BaseModel):
    """Retry configuration for nodes."""
    max_attempts: int = 3
    initial_interval_ms: int = 1000
    max_interval_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter: float = 0.1  # Random jitter factor
    retryable_errors: list[str] = Field(default_factory=list)  # Error types to retry
    non_retryable_errors: list[str] = Field(default_factory=list)  # Never retry these


class TimeoutPolicy(BaseModel):
    """Timeout configuration."""
    node_timeout_seconds: int = 300  # 5 minutes per node
    workflow_timeout_seconds: int = 86400  # 24 hours for workflow
    idle_timeout_seconds: int = 3600  # 1 hour idle before pause


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker for external services."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


# =============================================================================
# Execution Context
# =============================================================================

class ExecutionContext(BaseModel):
    """
    Context passed to each node during execution.
    
    Provides:
    - State access
    - Retry information
    - Timeout tracking
    - Circuit breaker status
    """
    execution_id: str
    workflow_id: str
    node_id: str
    
    # Retry state
    attempt: int = 1
    max_attempts: int = 3
    last_error: str | None = None
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: datetime | None = None
    
    # Circuit breaker
    circuit_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    
    # Flags
    is_retry: bool = False
    is_resuming: bool = False  # Resuming from checkpoint
    
    def is_timed_out(self) -> bool:
        """Check if execution has timed out."""
        if self.deadline and datetime.utcnow() > self.deadline:
            return True
        return False
    
    def remaining_time_seconds(self) -> float:
        """Get remaining time before timeout."""
        if not self.deadline:
            return float('inf')
        remaining = (self.deadline - datetime.utcnow()).total_seconds()
        return max(0, remaining)


# =============================================================================
# Node Execution Result
# =============================================================================

class NodeResult(BaseModel):
    """Result of executing a single node."""
    node_id: str
    status: ExecutionStatus
    
    # Output
    output: dict = Field(default_factory=dict)
    
    # Timing
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int = 0
    
    # Error info
    error: str | None = None
    error_type: str | None = None
    stack_trace: str | None = None
    
    # Retry info
    attempts: int = 1
    
    # Next node (for routing)
    next_node: str | None = None


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker for protecting external service calls.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject calls
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if call is allowed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed > self.config.timeout_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN


# =============================================================================
# Execution Engine
# =============================================================================

class ExecutionEngine:
    """
    Durable workflow execution engine.
    
    Features:
    - Crash recovery via checkpointing
    - Configurable retry policies
    - Circuit breakers for external calls
    - Timeout handling
    - Dead letter queue for failed executions
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        pool=None,
        default_retry_policy: RetryPolicy = None,
        default_timeout_policy: TimeoutPolicy = None,
    ):
        self.state_manager = state_manager
        self.pool = pool
        self.default_retry_policy = default_retry_policy or RetryPolicy()
        self.default_timeout_policy = default_timeout_policy or TimeoutPolicy()
        
        # Circuit breakers per service
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        
        # Dead letter queue (in-memory, would be Kafka in production)
        self._dead_letter_queue: list[dict] = []
        
        # Active executions
        self._active_executions: dict[str, ExecutionContext] = {}
    
    async def execute_node(
        self,
        node_func: Callable[[dict, ExecutionContext], Awaitable[dict]],
        node_id: str,
        execution_id: str,
        retry_policy: RetryPolicy = None,
        circuit_breaker_key: str = None,
    ) -> NodeResult:
        """
        Execute a single node with retry and circuit breaker protection.
        """
        policy = retry_policy or self.default_retry_policy
        started_at = datetime.utcnow()
        
        # Get current state
        state = self.state_manager.get_state(execution_id)
        if not state:
            return NodeResult(
                node_id=node_id,
                status=ExecutionStatus.FAILED,
                started_at=started_at,
                error="Execution state not found",
            )
        
        # Check circuit breaker
        if circuit_breaker_key:
            if circuit_breaker_key not in self._circuit_breakers:
                self._circuit_breakers[circuit_breaker_key] = CircuitBreaker(
                    CircuitBreakerConfig()
                )
            
            breaker = self._circuit_breakers[circuit_breaker_key]
            if not breaker.can_execute():
                return NodeResult(
                    node_id=node_id,
                    status=ExecutionStatus.FAILED,
                    started_at=started_at,
                    error="Circuit breaker open",
                    error_type="CircuitBreakerOpen",
                )
        
        # Execute with retries
        last_error = None
        last_error_type = None
        stack_trace = None
        
        for attempt in range(1, policy.max_attempts + 1):
            context = ExecutionContext(
                execution_id=execution_id,
                workflow_id=state.get("workflow_id", ""),
                node_id=node_id,
                attempt=attempt,
                max_attempts=policy.max_attempts,
                is_retry=attempt > 1,
                last_error=last_error,
                deadline=datetime.utcnow() + timedelta(
                    seconds=self.default_timeout_policy.node_timeout_seconds
                ),
            )
            
            try:
                # Execute node function
                result = await asyncio.wait_for(
                    node_func(state, context),
                    timeout=self.default_timeout_policy.node_timeout_seconds,
                )
                
                # Success - record and return
                if circuit_breaker_key:
                    self._circuit_breakers[circuit_breaker_key].record_success()
                
                completed_at = datetime.utcnow()
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)
                
                # Update state with result
                self.state_manager.update_state(
                    execution_id=execution_id,
                    updates={
                        "outputs": {node_id: result},
                        "execution_path": [node_id],
                    },
                    node_id=node_id,
                )
                
                return NodeResult(
                    node_id=node_id,
                    status=ExecutionStatus.COMPLETED,
                    output=result,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    attempts=attempt,
                    next_node=result.get("_next_node"),
                )
                
            except asyncio.TimeoutError:
                last_error = "Node execution timed out"
                last_error_type = "TimeoutError"
                
            except Exception as e:
                last_error = str(e)
                last_error_type = type(e).__name__
                stack_trace = traceback.format_exc()
                
                # Record circuit breaker failure
                if circuit_breaker_key:
                    self._circuit_breakers[circuit_breaker_key].record_failure()
                
                # Check if error is retryable
                if policy.non_retryable_errors and last_error_type in policy.non_retryable_errors:
                    break
                
                if policy.retryable_errors and last_error_type not in policy.retryable_errors:
                    # If retryable_errors specified, only retry those
                    if policy.retryable_errors:
                        break
            
            # Wait before retry (with exponential backoff)
            if attempt < policy.max_attempts:
                wait_ms = min(
                    policy.initial_interval_ms * (policy.backoff_multiplier ** (attempt - 1)),
                    policy.max_interval_ms,
                )
                # Add jitter
                import random
                jitter = wait_ms * policy.jitter * random.random()
                wait_ms += jitter
                
                logger.info(
                    "Retrying node",
                    node_id=node_id,
                    attempt=attempt + 1,
                    wait_ms=wait_ms,
                    error=last_error,
                )
                
                await asyncio.sleep(wait_ms / 1000)
        
        # All retries exhausted
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        # Update state with error
        self.state_manager.update_state(
            execution_id=execution_id,
            updates={
                "error": last_error,
                "error_node": node_id,
            },
            node_id=node_id,
        )
        
        # Add to dead letter queue
        self._add_to_dlq(execution_id, node_id, last_error, stack_trace)
        
        return NodeResult(
            node_id=node_id,
            status=ExecutionStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error=last_error,
            error_type=last_error_type,
            stack_trace=stack_trace,
            attempts=policy.max_attempts,
        )
    
    def _add_to_dlq(self, execution_id: str, node_id: str, error: str, stack_trace: str = None):
        """Add failed execution to dead letter queue."""
        dlq_entry = {
            "execution_id": execution_id,
            "node_id": node_id,
            "error": error,
            "stack_trace": stack_trace,
            "timestamp": datetime.utcnow().isoformat(),
            "state_snapshot": self.state_manager.get_state(execution_id),
        }
        
        self._dead_letter_queue.append(dlq_entry)
        
        logger.warning(
            "Added to dead letter queue",
            execution_id=execution_id,
            node_id=node_id,
            error=error,
        )
    
    def get_dlq_entries(self, limit: int = 100) -> list[dict]:
        """Get entries from dead letter queue."""
        return self._dead_letter_queue[-limit:]
    
    async def retry_from_dlq(self, dlq_index: int, node_func: Callable) -> NodeResult:
        """Retry a failed execution from dead letter queue."""
        if dlq_index >= len(self._dead_letter_queue):
            raise ValueError("Invalid DLQ index")
        
        entry = self._dead_letter_queue[dlq_index]
        
        # Restore state
        execution_id = entry["execution_id"]
        if entry["state_snapshot"]:
            self.state_manager._current_states[execution_id] = entry["state_snapshot"]
        
        # Retry execution
        result = await self.execute_node(
            node_func=node_func,
            node_id=entry["node_id"],
            execution_id=execution_id,
        )
        
        # Remove from DLQ if successful
        if result.status == ExecutionStatus.COMPLETED:
            self._dead_letter_queue.pop(dlq_index)
        
        return result
    
    async def resume_execution(
        self,
        execution_id: str,
        checkpoint_id: str = None,
    ) -> dict:
        """
        Resume a paused or failed execution.
        
        If checkpoint_id provided, resumes from that checkpoint.
        Otherwise resumes from last checkpoint.
        """
        # Get checkpoints
        checkpoints = self.state_manager.get_checkpoints(execution_id)
        if not checkpoints:
            raise ValueError("No checkpoints found for execution")
        
        # Find checkpoint to resume from
        if checkpoint_id:
            state = self.state_manager.rollback_to_checkpoint(execution_id, checkpoint_id)
        else:
            # Resume from last checkpoint
            last_checkpoint = checkpoints[-1]
            state = last_checkpoint.state
            self.state_manager._current_states[execution_id] = state.copy()
        
        logger.info(
            "Resuming execution",
            execution_id=execution_id,
            from_checkpoint=checkpoint_id or "latest",
        )
        
        return state
    
    def pause_execution(self, execution_id: str, reason: str = None):
        """Pause an execution (for human-in-loop)."""
        state = self.state_manager.get_state(execution_id)
        if state:
            self.state_manager.update_state(
                execution_id=execution_id,
                updates={
                    "_paused": True,
                    "_pause_reason": reason,
                    "_paused_at": datetime.utcnow().isoformat(),
                },
                create_checkpoint=True,
            )
            
            logger.info(
                "Paused execution",
                execution_id=execution_id,
                reason=reason,
            )
    
    def cancel_execution(self, execution_id: str):
        """Cancel an execution."""
        state = self.state_manager.get_state(execution_id)
        if state:
            self.state_manager.update_state(
                execution_id=execution_id,
                updates={
                    "_cancelled": True,
                    "_cancelled_at": datetime.utcnow().isoformat(),
                },
                create_checkpoint=True,
            )
            
            # Remove from active executions
            self._active_executions.pop(execution_id, None)
            
            logger.info("Cancelled execution", execution_id=execution_id)
