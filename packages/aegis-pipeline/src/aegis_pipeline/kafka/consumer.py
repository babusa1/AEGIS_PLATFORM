"""
Kafka Message Consumer

Async Kafka consumer for processing healthcare data streams.
"""

import json
from typing import Any, Callable, Awaitable
from datetime import datetime
import structlog

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord

logger = structlog.get_logger(__name__)


MessageHandler = Callable[[dict, dict], Awaitable[None]]


class KafkaMessageConsumer:
    """
    Async Kafka consumer for AEGIS pipeline.
    
    Usage:
        consumer = KafkaMessageConsumer(
            topics=["fhir.raw"],
            group_id="fhir-processor",
        )
        
        async def handle_message(value: dict, metadata: dict):
            print(f"Received: {value}")
        
        await consumer.start()
        await consumer.consume(handle_message)
    """
    
    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: str = "localhost:9092",
        auto_commit: bool = True,
    ):
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.auto_commit = auto_commit
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False
    
    async def start(self) -> None:
        """Start the Kafka consumer."""
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=self.auto_commit,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "Kafka consumer started",
            topics=self.topics,
            group=self.group_id,
        )
    
    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def consume(
        self,
        handler: MessageHandler,
        error_handler: Callable[[Exception, dict], Awaitable[None]] | None = None,
    ) -> None:
        """
        Consume messages and process with handler.
        
        Args:
            handler: Async function to process each message
            error_handler: Optional function to handle processing errors
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        
        async for record in self._consumer:
            if not self._running:
                break
            
            metadata = {
                "topic": record.topic,
                "partition": record.partition,
                "offset": record.offset,
                "timestamp": record.timestamp,
                "key": record.key.decode("utf-8") if record.key else None,
                "headers": dict(record.headers) if record.headers else {},
            }
            
            try:
                await handler(record.value, metadata)
            except Exception as e:
                logger.error(
                    "Message processing error",
                    topic=record.topic,
                    offset=record.offset,
                    error=str(e),
                )
                if error_handler:
                    await error_handler(e, {"value": record.value, "metadata": metadata})
    
    async def consume_batch(
        self,
        handler: Callable[[list[dict]], Awaitable[None]],
        batch_size: int = 100,
        timeout_ms: int = 1000,
    ) -> None:
        """
        Consume messages in batches.
        
        Args:
            handler: Async function to process each batch
            batch_size: Maximum batch size
            timeout_ms: Timeout for batch collection
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        
        while self._running:
            batch = await self._consumer.getmany(
                timeout_ms=timeout_ms,
                max_records=batch_size,
            )
            
            for tp, records in batch.items():
                if records:
                    values = [r.value for r in records]
                    await handler(values)
                    logger.debug(
                        "Processed batch",
                        topic=tp.topic,
                        count=len(records),
                    )
