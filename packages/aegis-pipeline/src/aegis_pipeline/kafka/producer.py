"""
Kafka Message Producer

Async Kafka producer for publishing healthcare data to topics.
"""

import json
from typing import Any
from datetime import datetime
import structlog

from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


class KafkaMessageProducer:
    """
    Async Kafka producer for AEGIS pipeline.
    
    Usage:
        producer = KafkaMessageProducer(bootstrap_servers="localhost:9092")
        await producer.start()
        
        await producer.send("fhir.raw", {"resourceType": "Patient", ...})
        
        await producer.stop()
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "aegis-producer",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer: AIOKafkaProducer | None = None
    
    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started", servers=self.bootstrap_servers)
    
    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send(
        self,
        topic: str,
        value: dict,
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Send a message to a Kafka topic.
        
        Args:
            topic: Kafka topic name
            value: Message value (dict, will be JSON serialized)
            key: Optional message key for partitioning
            headers: Optional message headers
        """
        if not self._producer:
            raise RuntimeError("Producer not started")
        
        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]
        
        await self._producer.send_and_wait(
            topic=topic,
            value=value,
            key=key,
            headers=kafka_headers,
        )
        
        logger.debug("Sent message", topic=topic, key=key)
    
    async def send_batch(
        self,
        topic: str,
        messages: list[dict],
        key_field: str | None = None,
    ) -> int:
        """
        Send multiple messages to a topic.
        
        Args:
            topic: Kafka topic name
            messages: List of message values
            key_field: Optional field in each message to use as key
            
        Returns:
            Number of messages sent
        """
        if not self._producer:
            raise RuntimeError("Producer not started")
        
        count = 0
        for msg in messages:
            key = msg.get(key_field) if key_field else None
            await self._producer.send(topic, value=msg, key=key)
            count += 1
        
        await self._producer.flush()
        logger.info("Sent batch", topic=topic, count=count)
        
        return count
    
    async def send_to_dlq(
        self,
        source_topic: str,
        value: dict,
        error: str,
        original_key: str | None = None,
    ) -> None:
        """
        Send a failed message to Dead Letter Queue.
        
        Args:
            source_topic: Original topic name
            value: Original message value
            error: Error message
            original_key: Original message key
        """
        dlq_topic = f"{source_topic.split('.')[0]}.dlq"
        
        dlq_message = {
            "original_topic": source_topic,
            "original_key": original_key,
            "original_value": value,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }
        
        await self.send(dlq_topic, dlq_message)
        logger.warning("Sent to DLQ", topic=dlq_topic, error=error)
