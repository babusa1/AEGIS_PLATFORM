"""
AEGIS Events Module

Event-driven processing:
- Kafka consumer
- Event handlers
- Real-time agent triggers
"""

from aegis.events.kafka_consumer import (
    EventType,
    EventPriority,
    HealthcareEvent,
    EventResult,
    EventHandler,
    KafkaEventConsumer,
    get_event_consumer,
    publish_event,
    router as events_router,
)

__all__ = [
    "EventType",
    "EventPriority",
    "HealthcareEvent",
    "EventResult",
    "EventHandler",
    "KafkaEventConsumer",
    "get_event_consumer",
    "publish_event",
    "events_router",
]
