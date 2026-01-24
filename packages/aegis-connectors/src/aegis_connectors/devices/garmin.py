"""Garmin Connect API Adapter"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.devices.base import DeviceAdapter, DeviceReading, MetricType

logger = structlog.get_logger(__name__)

@dataclass
class GarminCredentials:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None

class GarminAdapter(DeviceAdapter):
    """Garmin Connect API adapter. Supports activities, HR, stress, body battery."""
    
    METRIC_MAP = {"heartRate": MetricType.HEART_RATE, "steps": MetricType.STEPS,
        "stress": MetricType.STRESS, "bodyBattery": MetricType.ENERGY,
        "calories": MetricType.CALORIES, "floors": MetricType.FLOORS,
        "sleep": MetricType.SLEEP, "spo2": MetricType.SPO2}
    
    def __init__(self, credentials: GarminCredentials | None = None):
        self.credentials = credentials
        self.base_url = "https://apis.garmin.com"
    
    @property
    def device_type(self) -> str:
        return "garmin"
    
    async def fetch_data(self, user_id: str, start_date: datetime, end_date: datetime) -> list[DeviceReading]:
        """Fetch data from Garmin API. Returns stub data without credentials."""
        if not self.credentials:
            logger.warning("No Garmin credentials, returning sample data")
            return self._get_sample_readings(user_id, start_date)
        # Real implementation would call Garmin API
        return []
    
    def parse_response(self, data: dict) -> list[DeviceReading]:
        """Parse Garmin API response."""
        readings = []
        user_id = data.get("user_id", "")
        for entry in data.get("dailies", []):
            ts_str = entry.get("calendarDate", "")
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
            for key, metric_type in self.METRIC_MAP.items():
                if key in entry and entry[key] is not None:
                    readings.append(DeviceReading(device_type="garmin", metric_type=metric_type,
                        value=float(entry[key]), unit=self._get_unit(metric_type),
                        timestamp=ts, user_id=user_id))
        return readings
    
    def _get_unit(self, metric: MetricType) -> str:
        units = {MetricType.HEART_RATE: "bpm", MetricType.STEPS: "steps",
            MetricType.STRESS: "score", MetricType.ENERGY: "score",
            MetricType.CALORIES: "kcal", MetricType.SLEEP: "minutes", MetricType.SPO2: "%"}
        return units.get(metric, "")
    
    def _get_sample_readings(self, user_id: str, date: datetime) -> list[DeviceReading]:
        return [
            DeviceReading("garmin", MetricType.HEART_RATE, 68, "bpm", date, user_id),
            DeviceReading("garmin", MetricType.STEPS, 8500, "steps", date, user_id),
            DeviceReading("garmin", MetricType.STRESS, 35, "score", date, user_id),
            DeviceReading("garmin", MetricType.ENERGY, 75, "score", date, user_id),
        ]

SAMPLE_GARMIN = {"user_id": "GARMIN-USER-001", "dailies": [
    {"calendarDate": "2024-01-15", "heartRate": 68, "steps": 8500, "stress": 35,
     "bodyBattery": 75, "calories": 2200, "floors": 12}]}
