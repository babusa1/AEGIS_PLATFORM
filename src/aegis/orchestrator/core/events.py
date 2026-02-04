"""
Event Bus

Kafka-based event system for:
- Workflow events
- Agent communication
- CDC (Change Data Capture)
- External integrations
"""

from typing import Any, Callable, Awaitable
from datetime import datetime
from enum import Enum
import json
import uuid
import asyncio

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Event Models
# =============================================================================

class EventType(str, Enum):
    """Types of events."""
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    
    # Node events
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    NODE_FAILED = "node.failed"
    NODE_RETRYING = "node.retrying"
    
    # Agent events
    AGENT_INVOKED = "agent.invoked"
    AGENT_COMPLETED = "agent.completed"
    AGENT_HANDOFF = "agent.handoff"
    AGENT_APPROVAL_REQUIRED = "agent.approval_required"
    AGENT_APPROVAL_RECEIVED = "agent.approval_received"
    
    # Data events (CDC)
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    
    # Integration events
    WEBHOOK_RECEIVED = "webhook.received"
    EXTERNAL_CALL_STARTED = "external.call.started"
    EXTERNAL_CALL_COMPLETED = "external.call.completed"
    
    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    ALERT_RESOLVED = "alert.resolved"


class Event(BaseModel):
    """A single event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    
    # Source
    source: str  # Component that generated the event
    tenant_id: str = "default"
    
    # Payload
    data: dict = Field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None  # Links related events
    causation_id: str | None = None  # Event that caused this one
    
    # Routing
    topic: str | None = None  # Kafka topic
    partition_key: str | None = None  # For ordering
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "tenant_id": self.tenant_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        data["type"] = EventType(data["type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EventHandler(BaseModel):
    """Event handler registration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_types: list[EventType]
    handler_name: str
    filter_expression: str | None = None  # JSONPath filter
    
    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Event Bus
# =============================================================================

class EventBus:
    """
    Event bus for asynchronous communication.
    
    Features:
    - Publish/subscribe pattern
    - Event filtering
    - Kafka integration (optional)
    - In-memory fallback
    - Event replay
    - Dead letter handling
    """
    
    # Topic mapping
    TOPICS = {
        "workflows": ["workflow.*", "node.*"],
        "agents": ["agent.*"],
        "data": ["data.*"],
        "integrations": ["webhook.*", "external.*"],
        "alerts": ["alert.*"],
    }
    
    def __init__(self, kafka_producer=None, kafka_consumer=None):
        self.kafka_producer = kafka_producer
        self.kafka_consumer = kafka_consumer
        
        # In-memory handlers (for non-Kafka mode)
        self._handlers: dict[str, tuple[EventHandler, Callable]] = {}
        
        # Event history (for replay)
        self._event_history: list[Event] = []
        self._max_history = 10000
        
        # Dead letter queue
        self._dead_letters: list[tuple[Event, str]] = []
    
    # =========================================================================
    # Publishing
    # =========================================================================
    
    async def publish(
        self,
        event_type: EventType,
        source: str,
        data: dict,
        tenant_id: str = "default",
        correlation_id: str = None,
    ) -> Event:
        """Publish an event."""
        event = Event(
            type=event_type,
            source=source,
            data=data,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            topic=self._get_topic(event_type),
        )
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        # Publish to Kafka if available
        if self.kafka_producer:
            await self._publish_to_kafka(event)
        
        # Dispatch to in-memory handlers
        await self._dispatch(event)
        
        logger.debug(
            "Published event",
            event_type=event_type.value,
            event_id=event.id,
        )
        
        return event
    
    def _get_topic(self, event_type: EventType) -> str:
        """Get Kafka topic for event type."""
        event_prefix = event_type.value.split(".")[0]
        for topic, patterns in self.TOPICS.items():
            for pattern in patterns:
                if pattern.startswith(event_prefix):
                    return f"aegis.{topic}"
        return "aegis.default"
    
    async def _publish_to_kafka(self, event: Event):
        """Publish to Kafka."""
        if not self.kafka_producer:
            return
        
        try:
            await self.kafka_producer.send_and_wait(
                topic=event.topic or "aegis.default",
                value=event.to_json().encode(),
                key=event.partition_key.encode() if event.partition_key else None,
            )
        except Exception as e:
            logger.error("Failed to publish to Kafka", error=str(e))
            self._dead_letters.append((event, str(e)))
    
    # =========================================================================
    # Subscribing
    # =========================================================================
    
    def subscribe(
        self,
        event_types: list[EventType],
        handler: Callable[[Event], Awaitable[None]],
        handler_name: str = None,
        filter_expression: str = None,
    ) -> str:
        """Subscribe to events."""
        registration = EventHandler(
            event_types=event_types,
            handler_name=handler_name or handler.__name__,
            filter_expression=filter_expression,
        )
        
        self._handlers[registration.id] = (registration, handler)
        
        logger.info(
            "Subscribed to events",
            handler=registration.handler_name,
            event_types=[e.value for e in event_types],
        )
        
        return registration.id
    
    def unsubscribe(self, handler_id: str):
        """Unsubscribe from events."""
        self._handlers.pop(handler_id, None)
    
    async def _dispatch(self, event: Event):
        """Dispatch event to handlers."""
        for handler_id, (registration, handler) in self._handlers.items():
            if event.type not in registration.event_types:
                continue
            
            # Apply filter if configured
            if registration.filter_expression:
                if not self._matches_filter(event, registration.filter_expression):
                    continue
            
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "Handler failed",
                    handler=registration.handler_name,
                    event_id=event.id,
                    error=str(e),
                )
                self._dead_letters.append((event, str(e)))
    
    def _matches_filter(self, event: Event, filter_expression: str) -> bool:
        """Check if event matches filter (JSONPath)."""
        # Simplified filter - would use jsonpath_ng in production
        try:
            # Simple key=value filter
            if "=" in filter_expression:
                key, value = filter_expression.split("=")
                return str(event.data.get(key)) == value
        except:
            pass
        return True
    
    # =========================================================================
    # Event History & Replay
    # =========================================================================
    
    def get_history(
        self,
        event_type: EventType = None,
        source: str = None,
        since: datetime = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history."""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if source:
            events = [e for e in events if e.source == source]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    async def replay(
        self,
        events: list[Event],
        handler_ids: list[str] = None,
    ):
        """Replay events to handlers."""
        for event in events:
            if handler_ids:
                for handler_id in handler_ids:
                    if handler_id in self._handlers:
                        _, handler = self._handlers[handler_id]
                        await handler(event)
            else:
                await self._dispatch(event)
    
    def get_correlation_chain(self, correlation_id: str) -> list[Event]:
        """Get all events with a correlation ID."""
        return [
            e for e in self._event_history
            if e.correlation_id == correlation_id
        ]
    
    # =========================================================================
    # Dead Letter Queue
    # =========================================================================
    
    def get_dead_letters(self, limit: int = 100) -> list[tuple[Event, str]]:
        """Get dead letter events."""
        return self._dead_letters[-limit:]
    
    async def retry_dead_letter(self, index: int) -> bool:
        """Retry a dead letter event."""
        if index >= len(self._dead_letters):
            return False
        
        event, _ = self._dead_letters[index]
        
        try:
            await self._dispatch(event)
            self._dead_letters.pop(index)
            return True
        except Exception as e:
            logger.error("Dead letter retry failed", error=str(e))
            return False
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def emit_workflow_started(
        self,
        workflow_id: str,
        execution_id: str,
        inputs: dict,
        tenant_id: str = "default",
    ):
        """Emit workflow started event."""
        return await self.publish(
            event_type=EventType.WORKFLOW_STARTED,
            source="orchestrator",
            data={
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "inputs": inputs,
            },
            tenant_id=tenant_id,
            correlation_id=execution_id,
        )
    
    async def emit_workflow_completed(
        self,
        workflow_id: str,
        execution_id: str,
        outputs: dict,
        duration_ms: int,
        tenant_id: str = "default",
    ):
        """Emit workflow completed event."""
        return await self.publish(
            event_type=EventType.WORKFLOW_COMPLETED,
            source="orchestrator",
            data={
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "outputs": outputs,
                "duration_ms": duration_ms,
            },
            tenant_id=tenant_id,
            correlation_id=execution_id,
        )
    
    async def emit_node_started(
        self,
        execution_id: str,
        node_id: str,
        node_type: str,
        tenant_id: str = "default",
    ):
        """Emit node started event."""
        return await self.publish(
            event_type=EventType.NODE_STARTED,
            source="orchestrator",
            data={
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
            },
            tenant_id=tenant_id,
            correlation_id=execution_id,
        )
    
    async def emit_agent_invoked(
        self,
        agent_id: str,
        agent_name: str,
        query: str,
        execution_id: str = None,
        tenant_id: str = "default",
    ):
        """Emit agent invoked event."""
        return await self.publish(
            event_type=EventType.AGENT_INVOKED,
            source=f"agent.{agent_id}",
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "query": query[:200],  # Truncate
                "execution_id": execution_id,
            },
            tenant_id=tenant_id,
            correlation_id=execution_id,
        )
    
    async def emit_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        data: dict = None,
        tenant_id: str = "default",
    ):
        """Emit an alert event."""
        return await self.publish(
            event_type=EventType.ALERT_TRIGGERED,
            source="alerting",
            data={
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                **(data or {}),
            },
            tenant_id=tenant_id,
        )
