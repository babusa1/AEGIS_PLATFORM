"""
Google Fit Adapter
"""

from datetime import datetime
import structlog

from aegis_connectors.devices.base import DeviceAdapter, DeviceReading, MetricType

logger = structlog.get_logger(__name__)


class GoogleFitAdapter(DeviceAdapter):
    """Google Fit API adapter."""
    
    def __init__(self):
        self.access_token: str | None = None
        self.base_url = "https://www.googleapis.com/fitness/v1/users/me"
    
    @property
    def platform_name(self) -> str:
        return "google_fit"
    
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
        """Parse Google Fit API response."""
        readings = []
        
        for bucket in data.get("bucket", []):
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    ts = int(point.get("startTimeNanos", 0)) / 1e9
                    timestamp = datetime.fromtimestamp(ts)
                    
                    for val in point.get("value", []):
                        value = val.get("fpVal") or val.get("intVal", 0)
                        
                        readings.append(DeviceReading(
                            metric_type=MetricType.STEPS,
                            value=float(value),
                            unit="count",
                            timestamp=timestamp,
                            source_device="Google Fit",
                            source_platform=self.platform_name,
                        ))
        
        return readings
