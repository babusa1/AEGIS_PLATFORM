import pytest
import asyncio

from aegis.streaming.producer import KafkaProducer


@pytest.mark.asyncio
async def test_kafka_producer_send():
    p = KafkaProducer()
    res = await p.send(topic="aegis.events", key="k1", value={"event": "test"})
    assert res is True
    await p.stop()
