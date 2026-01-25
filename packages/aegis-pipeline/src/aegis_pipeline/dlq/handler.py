"""Dead Letter Queue Handler"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class FailureReason(str, Enum):
    VALIDATION = "validation"
    TRANSFORM = "transform"
    TIMEOUT = "timeout"
    SCHEMA = "schema"
    UNKNOWN = "unknown"


@dataclass
class FailedMessage:
    id: str
    topic: str
    payload: Any
    reason: FailureReason
    error: str
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_retry: datetime | None = None


class DLQHandler:
    """
    Dead Letter Queue for failed messages.
    
    SOC 2 Availability: Error handling
    """
    
    def __init__(self, max_retries: int = 3):
        self._queue: list[FailedMessage] = []
        self._max_retries = max_retries
    
    def add(self, message_id: str, topic: str, payload: Any,
           reason: FailureReason, error: str):
        """Add a failed message to DLQ."""
        msg = FailedMessage(
            id=message_id,
            topic=topic,
            payload=payload,
            reason=reason,
            error=error,
            max_retries=self._max_retries
        )
        self._queue.append(msg)
        logger.warning("Message added to DLQ", id=message_id, reason=reason.value)
    
    def get_retryable(self) -> list[FailedMessage]:
        """Get messages eligible for retry."""
        return [m for m in self._queue if m.retry_count < m.max_retries]
    
    def mark_retry(self, message_id: str, success: bool):
        """Mark retry attempt."""
        for msg in self._queue:
            if msg.id == message_id:
                msg.retry_count += 1
                msg.last_retry = datetime.utcnow()
                if success:
                    self._queue.remove(msg)
                break
    
    def get_by_reason(self, reason: FailureReason) -> list[FailedMessage]:
        """Get messages by failure reason."""
        return [m for m in self._queue if m.reason == reason]
    
    def get_stats(self) -> dict:
        """Get DLQ statistics."""
        return {
            "total": len(self._queue),
            "by_reason": {r.value: len([m for m in self._queue if m.reason == r])
                         for r in FailureReason},
            "retryable": len(self.get_retryable()),
            "exhausted": len([m for m in self._queue if m.retry_count >= m.max_retries])
        }
