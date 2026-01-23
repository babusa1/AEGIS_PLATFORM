"""
Device Adapter Base Class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from enum import Enum


class MetricType(str, Enum):
    """Types of health metrics from devices."""
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    DISTANCE = "distance"
    CALORIES = "calories"
    SLEEP = "sleep"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    WEIGHT = "weight"
    OXYGEN_SATURATION = "oxygen_saturation"
    RESPIRATORY_RATE = "respiratory_rate"
    BODY_TEMPERATURE = "body_temperature"
    ACTIVITY = "activity"
    WORKOUT = "workout"
    HRV = "heart_rate_variability"
    ECG = "ecg"


@dataclass
class DeviceReading:
    """Normalized device reading."""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    source_device: str
    source_platform: str
    metadata: dict | None = None
    
    def to_dict(self) -> dict:
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "source_device": self.source_device,
            "source_platform": self.source_platform,
            "metadata": self.metadata or {},
        }


class DeviceAdapter(ABC):
    """Base adapter for device platforms."""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass
    
    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool:
        """Authenticate with the platform."""
        pass
    
    @abstractmethod
    async def fetch_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[MetricType] | None = None,
    ) -> list[DeviceReading]:
        """Fetch data from the platform."""
        pass
    
    @abstractmethod
    def parse_response(self, data: dict) -> list[DeviceReading]:
        """Parse platform-specific response."""
        pass
