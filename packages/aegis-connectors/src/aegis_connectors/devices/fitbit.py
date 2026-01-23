"""
Fitbit Adapter
"""

from datetime import datetime
import structlog

from aegis_connectors.devices.base import DeviceAdapter, DeviceReading, MetricType

logger = structlog.get_logger(__name__)


class FitbitAdapter(DeviceAdapter):
    """Fitbit Web API adapter."""
    
    def __init__(self):
        self.access_token: str | None = None
        self.base_url = "https://api.fitbit.com/1/user/-"
    
    @property
    def platform_name(self) -> str:
        return "fitbit"
    
    async def authenticate(self, credentials: dict) -> bool:
        if "access_token" in credentials:
            self.access_token = credentials["access_token"]
            return True
        return False
    
    async def fetch_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[MetricType] | None = None,
    ) -> list[DeviceReading]:
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        return []
    
    def parse_response(self, data: dict) -> list[DeviceReading]:
        """Parse Fitbit API response."""
        readings = []
        
        # Parse heart rate
        for day in data.get("activities-heart", []):
            date_str = day.get("dateTime", "")
            value = day.get("value", {})
            resting_hr = value.get("restingHeartRate")
            
            if resting_hr:
                readings.append(DeviceReading(
                    metric_type=MetricType.HEART_RATE,
                    value=float(resting_hr),
                    unit="bpm",
                    timestamp=datetime.strptime(date_str, "%Y-%m-%d"),
                    source_device="Fitbit",
                    source_platform=self.platform_name,
                ))
        
        # Parse steps
        for day in data.get("activities-steps", []):
            readings.append(DeviceReading(
                metric_type=MetricType.STEPS,
                value=float(day.get("value", 0)),
                unit="count",
                timestamp=datetime.strptime(day.get("dateTime", ""), "%Y-%m-%d"),
                source_device="Fitbit",
                source_platform=self.platform_name,
            ))
        
        # Parse sleep
        for sleep in data.get("sleep", []):
            readings.append(DeviceReading(
                metric_type=MetricType.SLEEP,
                value=float(sleep.get("minutesAsleep", 0)),
                unit="minutes",
                timestamp=datetime.strptime(sleep.get("dateOfSleep", ""), "%Y-%m-%d"),
                source_device="Fitbit",
                source_platform=self.platform_name,
            ))
        
        return readings
