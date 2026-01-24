"""CDC Consumer for Debezium events"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import json
import structlog

logger = structlog.get_logger(__name__)


class CDCOperation(str, Enum):
    CREATE = "c"
    UPDATE = "u"
    DELETE = "d"
    READ = "r"


@dataclass
class CDCEvent:
    table: str
    operation: CDCOperation
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    timestamp: datetime
    source: str


class CDCConsumer:
    """Consume CDC events from Debezium via Kafka."""
    
    def __init__(self, bootstrap_servers: str, group_id: str = "aegis-cdc"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._handlers: dict[str, list[Callable]] = {}
        self._consumer = None
    
    def on_change(self, table: str):
        """Decorator to register a handler for table changes."""
        def decorator(func: Callable[[CDCEvent], None]):
            if table not in self._handlers:
                self._handlers[table] = []
            self._handlers[table].append(func)
            return func
        return decorator
    
    async def start(self, topics: list[str]):
        """Start consuming CDC events."""
        try:
            from aiokafka import AIOKafkaConsumer
            self._consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                value_deserializer=lambda m: json.loads(m.decode())
            )
            await self._consumer.start()
            logger.info("CDC consumer started", topics=topics)
            
            async for msg in self._consumer:
                await self._process_message(msg)
                
        except ImportError:
            logger.warning("aiokafka not installed, CDC disabled")
        except Exception as e:
            logger.error("CDC consumer error", error=str(e))
    
    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
    
    async def _process_message(self, msg):
        try:
            payload = msg.value
            if not payload:
                return
            
            # Parse Debezium event
            event = self._parse_event(msg.topic, payload)
            if not event:
                return
            
            # Call handlers
            handlers = self._handlers.get(event.table, [])
            handlers.extend(self._handlers.get("*", []))
            
            for handler in handlers:
                try:
                    await handler(event) if hasattr(handler, "__await__") else handler(event)
                except Exception as e:
                    logger.error("Handler error", table=event.table, error=str(e))
                    
        except Exception as e:
            logger.error("Message processing error", error=str(e))
    
    def _parse_event(self, topic: str, payload: dict) -> CDCEvent | None:
        try:
            # Extract table name from topic (format: prefix.schema.table)
            parts = topic.split(".")
            table = parts[-1] if parts else topic
            
            # Get operation
            op = payload.get("op", "r")
            operation = CDCOperation(op) if op in [e.value for e in CDCOperation] else CDCOperation.READ
            
            # Get before/after states
            before = payload.get("before")
            after = payload.get("after")
            
            # Get timestamp
            ts_ms = payload.get("ts_ms", 0)
            timestamp = datetime.fromtimestamp(ts_ms / 1000) if ts_ms else datetime.utcnow()
            
            # Get source info
            source = payload.get("source", {}).get("table", table)
            
            return CDCEvent(
                table=table,
                operation=operation,
                before=before,
                after=after,
                timestamp=timestamp,
                source=source
            )
        except Exception as e:
            logger.error("Event parsing error", error=str(e))
            return None


# Example usage
async def example_cdc_setup():
    consumer = CDCConsumer("localhost:9092")
    
    @consumer.on_change("patients")
    async def handle_patient_change(event: CDCEvent):
        if event.operation == CDCOperation.CREATE:
            logger.info("New patient created", patient=event.after)
        elif event.operation == CDCOperation.UPDATE:
            logger.info("Patient updated", before=event.before, after=event.after)
    
    @consumer.on_change("observations")
    async def handle_observation(event: CDCEvent):
        if event.operation == CDCOperation.CREATE:
            logger.info("New observation", data=event.after)
    
    await consumer.start(["aegis.public.patients", "aegis.public.observations"])
