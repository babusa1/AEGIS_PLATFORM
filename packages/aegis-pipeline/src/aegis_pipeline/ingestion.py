"""
Data Ingestion Pipeline

Orchestrates connectors, Kafka, validation, and graph writing.
"""

from typing import Any
from datetime import datetime
from dataclasses import dataclass, field
import structlog

from aegis_pipeline.kafka.producer import KafkaMessageProducer
from aegis_pipeline.kafka.consumer import KafkaMessageConsumer
from aegis_pipeline.quality.validator import DataQualityValidator, ValidationReport

logger = structlog.get_logger(__name__)


@dataclass
class IngestionResult:
    """Result of ingestion operation."""
    success: bool
    records_processed: int = 0
    records_valid: int = 0
    records_invalid: int = 0
    vertices_created: int = 0
    edges_created: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0


class IngestionPipeline:
    """
    Orchestrates data ingestion pipeline.
    
    Flow:
    1. Raw data arrives (FHIR, HL7v2, etc.)
    2. Connector parses and transforms to vertices/edges
    3. Validator checks data quality
    4. Valid data sent to validated topic
    5. Invalid data sent to DLQ
    6. Graph writer persists to JanusGraph
    
    Usage:
        pipeline = IngestionPipeline(
            kafka_servers="localhost:9092",
            graph_writer=graph_writer,
        )
        await pipeline.start()
        
        # Ingest FHIR data
        result = await pipeline.ingest_fhir(fhir_bundle, tenant_id="hospital-a")
    """
    
    def __init__(
        self,
        kafka_servers: str = "localhost:9092",
        graph_writer: Any = None,
        validator: DataQualityValidator | None = None,
    ):
        self.kafka_servers = kafka_servers
        self.graph_writer = graph_writer
        self.validator = validator or DataQualityValidator()
        
        self._producer: KafkaMessageProducer | None = None
    
    async def start(self) -> None:
        """Start the pipeline."""
        self._producer = KafkaMessageProducer(
            bootstrap_servers=self.kafka_servers,
            client_id="aegis-ingestion",
        )
        await self._producer.start()
        logger.info("Ingestion pipeline started")
    
    async def stop(self) -> None:
        """Stop the pipeline."""
        if self._producer:
            await self._producer.stop()
        logger.info("Ingestion pipeline stopped")
    
    async def ingest_fhir(
        self,
        data: Any,
        tenant_id: str,
        source_system: str = "fhir",
    ) -> IngestionResult:
        """
        Ingest FHIR data.
        
        Args:
            data: FHIR Bundle or Resource (JSON string or dict)
            tenant_id: Tenant ID for data isolation
            source_system: Source system identifier
        """
        from aegis_connectors.fhir import FHIRConnector
        
        start = datetime.utcnow()
        result = IngestionResult(success=True)
        
        try:
            # Parse FHIR
            connector = FHIRConnector(tenant_id=tenant_id, source_system=source_system)
            parse_result = await connector.parse(data)
            
            if not parse_result.success:
                result.errors.extend(parse_result.errors)
            
            result.records_processed = parse_result.vertex_count
            
            # Validate and process each vertex
            for vertex in parse_result.vertices:
                label = vertex.get("label", "Unknown")
                report = self.validator.validate(vertex, label)
                
                if report.valid:
                    result.records_valid += 1
                    
                    # Send to validated topic
                    if self._producer:
                        await self._producer.send(
                            topic="fhir.validated",
                            value=vertex,
                            key=vertex.get("id"),
                        )
                    
                    # Write to graph
                    if self.graph_writer:
                        await self.graph_writer.upsert_vertex(
                            label=label,
                            id_value=vertex.get("id"),
                            tenant_id=tenant_id,
                            properties=vertex,
                        )
                        result.vertices_created += 1
                else:
                    result.records_invalid += 1
                    
                    # Send to DLQ
                    if self._producer:
                        await self._producer.send_to_dlq(
                            source_topic="fhir.raw",
                            value=vertex,
                            error="; ".join(e.message for e in report.errors),
                        )
            
            # Process edges
            for edge in parse_result.edges:
                if self.graph_writer:
                    try:
                        await self.graph_writer.create_edge(
                            from_label=edge["from_label"],
                            from_id=edge["from_id"],
                            edge_label=edge["label"],
                            to_label=edge["to_label"],
                            to_id=edge["to_id"],
                            tenant_id=tenant_id,
                        )
                        result.edges_created += 1
                    except Exception as e:
                        logger.warning("Edge creation failed", error=str(e))
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error("FHIR ingestion failed", error=str(e))
        
        result.duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        
        logger.info(
            "FHIR ingestion complete",
            valid=result.records_valid,
            invalid=result.records_invalid,
            vertices=result.vertices_created,
            edges=result.edges_created,
            duration_ms=result.duration_ms,
        )
        
        return result
    
    async def ingest_hl7(
        self,
        message: str,
        tenant_id: str,
        source_system: str = "hl7v2",
    ) -> IngestionResult:
        """Ingest HL7v2 message."""
        from aegis_connectors.hl7v2 import HL7v2Connector
        
        start = datetime.utcnow()
        result = IngestionResult(success=True)
        
        try:
            connector = HL7v2Connector(tenant_id=tenant_id, source_system=source_system)
            parse_result = await connector.parse(message)
            
            if not parse_result.success:
                result.errors.extend(parse_result.errors)
            
            result.records_processed = parse_result.vertex_count
            
            for vertex in parse_result.vertices:
                label = vertex.get("label", "Unknown")
                report = self.validator.validate(vertex, label)
                
                if report.valid:
                    result.records_valid += 1
                    
                    if self._producer:
                        await self._producer.send(
                            topic="hl7.validated",
                            value=vertex,
                            key=vertex.get("id"),
                        )
                    
                    if self.graph_writer:
                        await self.graph_writer.upsert_vertex(
                            label=label,
                            id_value=vertex.get("id"),
                            tenant_id=tenant_id,
                            properties=vertex,
                        )
                        result.vertices_created += 1
                else:
                    result.records_invalid += 1
                    
                    if self._producer:
                        await self._producer.send_to_dlq(
                            source_topic="hl7.raw",
                            value=vertex,
                            error="; ".join(e.message for e in report.errors),
                        )
            
            for edge in parse_result.edges:
                if self.graph_writer:
                    try:
                        await self.graph_writer.create_edge(
                            from_label=edge["from_label"],
                            from_id=edge["from_id"],
                            edge_label=edge["label"],
                            to_label=edge["to_label"],
                            to_id=edge["to_id"],
                            tenant_id=tenant_id,
                        )
                        result.edges_created += 1
                    except Exception:
                        pass
            
        except ImportError:
            result.success = False
            result.errors.append("HL7v2 connector requires hl7apy")
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        result.duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return result
