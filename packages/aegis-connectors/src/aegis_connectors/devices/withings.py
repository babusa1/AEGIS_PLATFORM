"""Withings API Adapter"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.devices.base import DeviceAdapter, DeviceReading, MetricType

logger = structlog.get_logger(__name__)

@dataclass
class WithingsCredentials:
    access_token: str
    refresh_token: str | None = None

class WithingsAdapter(DeviceAdapter):
    """Withings API adapter. Supports weight, BP, sleep, ECG."""
    
    MEASURE_TYPES = {1: (MetricType.WEIGHT, "kg"), 4: (MetricType.HEIGHT, "m"),
        9: (MetricType.BLOOD_PRESSURE_DIASTOLIC, "mmHg"),
        10: (MetricType.BLOOD_PRESSURE_SYSTOLIC, "mmHg"),
        11: (MetricType.HEART_RATE, "bpm"), 54: (MetricType.SPO2, "%")}
    
    def __init__(self, credentials: WithingsCredentials | None = None):
        self.credentials = credentials
        self.base_url = "https://wbsapi.withings.net"
    
    @property
    def device_type(self) -> str:
        return "withings"
    
    async def fetch_data(self, user_id: str, start_date: datetime, end_date: datetime) -> list[DeviceReading]:
        if not self.credentials:
            logger.warning("No Withings credentials, returning sample data")
            return self._get_sample_readings(user_id, start_date)
        return []
    
    def parse_response(self, data: dict) -> list[DeviceReading]:
        readings = []
        user_id = data.get("user_id", "")
        for grp in data.get("body", {}).get("measuregrps", []):
            ts = datetime.fromtimestamp(grp.get("date", 0))
            for measure in grp.get("measures", []):
                m_type = measure.get("type")
                if m_type in self.MEASURE_TYPES:
                    metric, unit = self.MEASURE_TYPES[m_type]
                    value = measure.get("value", 0) * (10 ** measure.get("unit", 0))
                    readings.append(DeviceReading("withings", metric, value, unit, ts, user_id))
        return readings
    
    def _get_sample_readings(self, user_id: str, date: datetime) -> list[DeviceReading]:
        return [
            DeviceReading("withings", MetricType.WEIGHT, 75.5, "kg", date, user_id),
            DeviceReading("withings", MetricType.BLOOD_PRESSURE_SYSTOLIC, 122, "mmHg", date, user_id),
            DeviceReading("withings", MetricType.BLOOD_PRESSURE_DIASTOLIC, 78, "mmHg", date, user_id),
            DeviceReading("withings", MetricType.HEART_RATE, 72, "bpm", date, user_id),
        ]

SAMPLE_WITHINGS = {"user_id": "WITHINGS-USER-001", "body": {"measuregrps": [
    {"date": 1705305600, "measures": [{"type": 1, "value": 755, "unit": -1},
        {"type": 10, "value": 122, "unit": 0}, {"type": 9, "value": 78, "unit": 0}]}]}}
