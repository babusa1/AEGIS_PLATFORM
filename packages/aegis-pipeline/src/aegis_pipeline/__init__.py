"""
AEGIS Data Pipeline

Kafka-based streaming pipeline with data quality validation.
"""

from aegis_pipeline.kafka.producer import KafkaMessageProducer
from aegis_pipeline.kafka.consumer import KafkaMessageConsumer
from aegis_pipeline.quality.validator import DataQualityValidator

__version__ = "0.1.0"

__all__ = [
    "KafkaMessageProducer",
    "KafkaMessageConsumer", 
    "DataQualityValidator",
]
