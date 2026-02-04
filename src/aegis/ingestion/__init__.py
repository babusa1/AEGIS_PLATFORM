"""
AEGIS Data Ingestion Module

Parsers and writers for healthcare data standards:
- FHIR R4
- HL7v2
- EDI X12 (837, 835, 270/271, 276/277, 278)

Also includes:
- Streaming ingestion service (Kafka-based)
- Synthetic data generation for testing
"""

from aegis.ingestion.fhir_parser import FHIRParser
from aegis.ingestion.graph_writer import GraphWriter
from aegis.ingestion.synthetic_data import SyntheticDataGenerator
from aegis.ingestion.service import IngestionService
from aegis.ingestion.streaming import (
    StreamingIngestionService,
    StreamingMessage,
    StreamingTopic,
    MessageStatus,
    ProcessingResult,
    get_streaming_service,
    start_streaming_ingestion,
    stop_streaming_ingestion,
)

__all__ = [
    # Core ingestion
    "FHIRParser",
    "GraphWriter", 
    "SyntheticDataGenerator",
    "IngestionService",
    # Streaming
    "StreamingIngestionService",
    "StreamingMessage",
    "StreamingTopic",
    "MessageStatus",
    "ProcessingResult",
    "get_streaming_service",
    "start_streaming_ingestion",
    "stop_streaming_ingestion",
]
