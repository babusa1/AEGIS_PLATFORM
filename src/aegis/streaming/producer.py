"""Streaming producer skeleton (Kafka compatible)

Provides a simple async producer interface that can be replaced with aiokafka
or confluent-kafka implementations in production.
"""

from typing import Any, Dict
import asyncio
import json

import structlog

logger = structlog.get_logger(__name__)


class KafkaProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._running = False

    async def start(self):
        logger.info("KafkaProducer.start", servers=self.bootstrap_servers)
        await asyncio.sleep(0.01)
        self._running = True

    async def send(self, topic: str, key: str | None, value: Dict[str, Any]) -> bool:
        if not self._running:
            await self.start()
        payload = json.dumps(value)
        logger.debug("KafkaProducer.send", topic=topic, key=key, payload_len=len(payload))
        # In prod: send to Kafka
        await asyncio.sleep(0.005)
        return True

    async def stop(self):
        logger.info("KafkaProducer.stop")
        self._running = False
