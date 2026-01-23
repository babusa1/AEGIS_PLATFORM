"""
Device Connector

Main connector that uses platform adapters.
"""

from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.devices.base import DeviceReading, MetricType

logger = structlog.get_logger(__name__)


class DeviceConnector(BaseConnector):
    """
    Device/Wearable Connector.
    
    Transforms device readings to graph vertices.
    
    Usage:
        connector = DeviceConnector(tenant_id="hospital-a")
        result = await connector.parse(readings)
    """
    
    def __init__(
        self,
        tenant_id: str,
        source_system: str = "devices",
        patient_id: str | None = None,
    ):
        super().__init__(tenant_id, source_system)
        self.patient_id = patient_id
    
    @property
    def connector_type(self) -> str:
        return "devices"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """
        Parse device readings.
        
        Args:
            data: List of DeviceReading objects or dicts
        """
        vertices = []
        edges = []
        errors = []
        
        if not isinstance(data, list):
            data = [data]
        
        for i, reading in enumerate(data):
            try:
                if isinstance(reading, DeviceReading):
                    vertex = self._reading_to_vertex(reading, i)
                elif isinstance(reading, dict):
                    vertex = self._dict_to_vertex(reading, i)
                else:
                    errors.append(f"Invalid reading type: {type(reading)}")
                    continue
                
                vertices.append(vertex)
                
                # Create edge to patient if set
                if self.patient_id:
                    edges.append({
                        "label": "HAS_DEVICE_READING",
                        "from_label": "Patient",
                        "from_id": f"Patient/{self.patient_id}",
                        "to_label": "DeviceReading",
                        "to_id": vertex["id"],
                        "tenant_id": self.tenant_id,
                    })
                    
            except Exception as e:
                errors.append(f"Reading {i}: {str(e)}")
        
        logger.info(
            "Device parse complete",
            readings=len(vertices),
            errors=len(errors),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={"reading_count": len(vertices)},
        )
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if not isinstance(data, (list, DeviceReading, dict)):
            errors.append("Data must be list, DeviceReading, or dict")
        return errors
    
    def _reading_to_vertex(self, reading: DeviceReading, index: int) -> dict:
        """Convert DeviceReading to vertex."""
        ts = reading.timestamp.strftime("%Y%m%d%H%M%S")
        reading_id = f"DeviceReading/{reading.source_platform}-{ts}-{index}"
        
        return {
            "label": "DeviceReading",
            "id": reading_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "metric_type": reading.metric_type.value,
            "value": reading.value,
            "unit": reading.unit,
            "timestamp": reading.timestamp.isoformat(),
            "source_device": reading.source_device,
            "source_platform": reading.source_platform,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def _dict_to_vertex(self, data: dict, index: int) -> dict:
        """Convert dict to vertex."""
        ts = data.get("timestamp", datetime.utcnow().isoformat())
        platform = data.get("source_platform", "unknown")
        reading_id = f"DeviceReading/{platform}-{index}"
        
        return {
            "label": "DeviceReading",
            "id": reading_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "metric_type": data.get("metric_type", "unknown"),
            "value": data.get("value", 0),
            "unit": data.get("unit", ""),
            "timestamp": ts,
            "source_device": data.get("source_device", ""),
            "source_platform": platform,
            "created_at": datetime.utcnow().isoformat(),
        }
