"""
X12 Connector
"""

from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.x12.parser import X12Parser
from aegis_connectors.x12.transformer import X12Transformer

logger = structlog.get_logger(__name__)


class X12Connector(BaseConnector):
    """
    X12 EDI Connector.
    
    Parses 837/835 claims and transforms to graph vertices.
    
    Usage:
        connector = X12Connector(tenant_id="payer-a")
        result = await connector.parse(x12_data)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "x12"):
        super().__init__(tenant_id, source_system)
        self.parser = X12Parser()
        self.transformer = X12Transformer(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "x12"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse X12 data and transform to graph."""
        errors = []
        
        if not isinstance(data, str):
            return ConnectorResult(success=False, errors=["X12 data must be string"])
        
        parsed, parse_errors = self.parser.parse(data)
        errors.extend(parse_errors)
        
        if not parsed:
            return ConnectorResult(success=False, errors=errors)
        
        try:
            vertices, edges = self.transformer.transform(parsed)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "X12 parse complete",
            type=parsed.transaction_type,
            claims=len(parsed.claims),
            remittances=len(parsed.remittances),
            vertices=len(vertices),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "transaction_type": parsed.transaction_type,
                "claims_count": len(parsed.claims),
                "remittances_count": len(parsed.remittances),
            }
        )
    
    async def validate(self, data: Any) -> list[str]:
        if not isinstance(data, str):
            return ["X12 data must be string"]
        return self.parser.validate(data)


# Sample X12 837P for testing
SAMPLE_837P = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *240115*1200*^*00501*000000001*0*P*:~
GS*HC*SENDER*RECEIVER*20240115*1200*1*X*005010X222A1~
ST*837*0001*005010X222A1~
BHT*0019*00*1234*20240115*1200*CH~
NM1*41*2*BILLING PROVIDER*****XX*1234567890~
NM1*40*2*RECEIVER NAME*****46*12345~
HL*1**20*1~
NM1*85*2*BILLING PROVIDER*****XX*1234567890~
HL*2*1*22*0~
NM1*IL*1*SMITH*JOHN****MI*ABC123456~
NM1*QC*1*SMITH*JOHN~
CLM*CLAIM001*150.00***11:B:1*Y*A*Y*Y~
HI*ABK:J06.9~
LX*1~
SV1*HC:99213*75.00*UN*1***1~
DTP*472*D8*20240115~
LX*2~
SV1*HC:99214*75.00*UN*1***1~
DTP*472*D8*20240115~
SE*20*0001~
GE*1*1~
IEA*1*000000001~"""
