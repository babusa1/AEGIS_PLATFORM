"""
HL7v2 Connector

Main connector class for HL7v2 messages.
"""

from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.hl7v2.parser import HL7v2Parser, HL7APY_AVAILABLE
from aegis_connectors.hl7v2.transformer import HL7v2Transformer

logger = structlog.get_logger(__name__)


class HL7v2Connector(BaseConnector):
    """
    HL7v2 Connector.
    
    Parses ADT, ORU, ORM messages and transforms to graph vertices.
    
    Usage:
        connector = HL7v2Connector(tenant_id="hospital-a")
        result = await connector.parse(hl7_message_string)
        
        for vertex in result.vertices:
            await graph.create_vertex(vertex["label"], vertex)
    """
    
    def __init__(
        self,
        tenant_id: str,
        source_system: str = "hl7v2",
    ):
        super().__init__(tenant_id, source_system)
        
        if not HL7APY_AVAILABLE:
            raise ImportError("hl7apy required. Install with: pip install aegis-connectors[hl7]")
        
        self.parser = HL7v2Parser()
        self.transformer = HL7v2Transformer(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "hl7v2"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """
        Parse an HL7v2 message and transform to graph vertices/edges.
        
        Args:
            data: Raw HL7v2 message string
            
        Returns:
            ConnectorResult with vertices and edges
        """
        errors = []
        warnings = []
        
        if not isinstance(data, str):
            return ConnectorResult(
                success=False,
                errors=["HL7v2 data must be a string"]
            )
        
        # Parse message
        parsed, parse_errors = self.parser.parse(data)
        errors.extend(parse_errors)
        
        if not parsed:
            return ConnectorResult(
                success=False,
                errors=errors,
            )
        
        # Transform to vertices/edges
        try:
            vertices, edges = self.transformer.transform(parsed)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "HL7v2 parse complete",
            message_type=parsed.message_type,
            trigger_event=parsed.trigger_event,
            vertices=len(vertices),
            edges=len(edges),
            tenant=self.tenant_id,
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            warnings=warnings,
            metadata={
                "message_type": parsed.message_type,
                "trigger_event": parsed.trigger_event,
                "message_control_id": parsed.message_control_id,
                "connector_type": self.connector_type,
            }
        )
    
    async def validate(self, data: Any) -> list[str]:
        """Validate an HL7v2 message without full parsing."""
        if not isinstance(data, str):
            return ["HL7v2 data must be a string"]
        
        return self.parser.validate(data)
    
    async def parse_batch(self, messages: list[str]) -> list[ConnectorResult]:
        """
        Parse multiple HL7v2 messages.
        
        Args:
            messages: List of HL7v2 message strings
            
        Returns:
            List of ConnectorResults
        """
        results = []
        
        for msg in messages:
            result = await self.parse(msg)
            results.append(result)
        
        return results


# Sample HL7v2 messages for testing
SAMPLE_ADT_A01 = """MSH|^~\\&|EPIC|HOSPITAL|AEGIS|AEGIS|20240115120000||ADT^A01|MSG001|P|2.5
PID|1||12345^^^MRN||SMITH^JOHN^A||19800115|M|||123 MAIN ST^^SPRINGFIELD^IL^62701||555-123-4567||S||12345|123-45-6789
PV1|1|I|3W^301^A^HOSPITAL||||1234567890^JONES^MARY^MD|||||||||||1234567890|||||||||||||||||||||||||20240115100000
DG1|1||I10^Essential hypertension^ICD10|||A
IN1|1|BCBS|12345|BLUE CROSS BLUE SHIELD|PO BOX 1234^^CHICAGO^IL^60601|||GRP123|ABC COMPANY|||||20240101|20241231"""

SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|AEGIS|AEGIS|20240115140000||ORU^R01|MSG002|P|2.5
PID|1||12345^^^MRN||SMITH^JOHN^A||19800115|M
OBX|1|NM|2345-7^Glucose^LN||110|mg/dL|70-100|H|||F|||20240115130000
OBX|2|NM|718-7^Hemoglobin^LN||14.2|g/dL|12.0-17.5|N|||F|||20240115130000
OBX|3|NM|6690-2^WBC^LN||7.5|K/uL|4.5-11.0|N|||F|||20240115130000"""
