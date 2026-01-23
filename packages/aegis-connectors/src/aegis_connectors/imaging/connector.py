"""
Imaging Connector
"""

from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.imaging.parser import DICOMParser
from aegis_connectors.imaging.transformer import ImagingTransformer

logger = structlog.get_logger(__name__)


class ImagingConnector(BaseConnector):
    """
    DICOM Imaging Connector.
    
    Parses DICOM metadata and transforms to graph vertices.
    
    Usage:
        connector = ImagingConnector(tenant_id="hospital-a")
        result = await connector.parse(dicom_json)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "imaging"):
        super().__init__(tenant_id, source_system)
        self.parser = DICOMParser()
        self.transformer = ImagingTransformer(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "imaging"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse DICOM metadata."""
        errors = []
        
        if isinstance(data, dict) and "study_instance_uid" in data:
            # Tag dictionary format
            parsed, parse_errors = self.parser.parse_tags(data)
        else:
            # DICOM JSON format
            parsed, parse_errors = self.parser.parse_json(data)
        
        errors.extend(parse_errors)
        
        if not parsed:
            return ConnectorResult(success=False, errors=errors)
        
        try:
            vertices, edges = self.transformer.transform(parsed)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "Imaging parse complete",
            study_uid=parsed.study_instance_uid,
            modalities=parsed.modalities,
            vertices=len(vertices),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "study_instance_uid": parsed.study_instance_uid,
                "modalities": parsed.modalities,
                "patient_id": parsed.patient_id,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        return self.parser.validate(data)


# Sample DICOM JSON for testing
SAMPLE_DICOM_JSON = {
    "0020000D": {"vr": "UI", "Value": ["1.2.840.113619.2.55.3.4271045733"]},
    "00200010": {"vr": "SH", "Value": ["STUDY001"]},
    "00080020": {"vr": "DA", "Value": ["20240115"]},
    "00080030": {"vr": "TM", "Value": ["103000"]},
    "00081030": {"vr": "LO", "Value": ["CT CHEST W/CONTRAST"]},
    "00080050": {"vr": "SH", "Value": ["ACC123456"]},
    "00080060": {"vr": "CS", "Value": ["CT"]},
    "00080080": {"vr": "LO", "Value": ["General Hospital"]},
    "00080090": {"vr": "PN", "Value": [{"Alphabetic": "Smith^John^MD"}]},
    "00100020": {"vr": "LO", "Value": ["PAT12345"]},
    "00100010": {"vr": "PN", "Value": [{"Alphabetic": "Doe^Jane"}]},
}
