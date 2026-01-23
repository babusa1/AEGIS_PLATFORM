"""
Apple HealthKit Adapter

Parses HealthKit export data (XML format).
"""

from datetime import datetime
from typing import Any
import xml.etree.ElementTree as ET
import structlog

from aegis_connectors.devices.base import DeviceAdapter, DeviceReading, MetricType

logger = structlog.get_logger(__name__)


# HealthKit type to MetricType mapping
HEALTHKIT_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": MetricType.HEART_RATE,
    "HKQuantityTypeIdentifierStepCount": MetricType.STEPS,
    "HKQuantityTypeIdentifierDistanceWalkingRunning": MetricType.DISTANCE,
    "HKQuantityTypeIdentifierActiveEnergyBurned": MetricType.CALORIES,
    "HKQuantityTypeIdentifierBasalEnergyBurned": MetricType.CALORIES,
    "HKQuantityTypeIdentifierBloodPressureSystolic": MetricType.BLOOD_PRESSURE,
    "HKQuantityTypeIdentifierBloodPressureDiastolic": MetricType.BLOOD_PRESSURE,
    "HKQuantityTypeIdentifierBloodGlucose": MetricType.BLOOD_GLUCOSE,
    "HKQuantityTypeIdentifierBodyMass": MetricType.WEIGHT,
    "HKQuantityTypeIdentifierOxygenSaturation": MetricType.OXYGEN_SATURATION,
    "HKQuantityTypeIdentifierRespiratoryRate": MetricType.RESPIRATORY_RATE,
    "HKQuantityTypeIdentifierBodyTemperature": MetricType.BODY_TEMPERATURE,
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": MetricType.HRV,
    "HKCategoryTypeIdentifierSleepAnalysis": MetricType.SLEEP,
}


class HealthKitAdapter(DeviceAdapter):
    """
    Apple HealthKit adapter.
    
    Parses HealthKit XML export files.
    """
    
    @property
    def platform_name(self) -> str:
        return "apple_healthkit"
    
    async def authenticate(self, credentials: dict) -> bool:
        # HealthKit uses file export, no auth needed
        return True
    
    async def fetch_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[MetricType] | None = None,
    ) -> list[DeviceReading]:
        # HealthKit requires file upload, not API fetch
        raise NotImplementedError("Use parse_export() for HealthKit data")
    
    def parse_response(self, data: dict) -> list[DeviceReading]:
        raise NotImplementedError("Use parse_export() for HealthKit")
    
    def parse_export(
        self,
        xml_data: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DeviceReading]:
        """
        Parse HealthKit XML export.
        
        Args:
            xml_data: Raw XML string from HealthKit export
            start_date: Filter readings after this date
            end_date: Filter readings before this date
        """
        readings = []
        
        try:
            root = ET.fromstring(xml_data)
            
            for record in root.findall(".//Record"):
                reading = self._parse_record(record)
                if reading:
                    # Apply date filter
                    if start_date and reading.timestamp < start_date:
                        continue
                    if end_date and reading.timestamp > end_date:
                        continue
                    readings.append(reading)
            
            logger.info(f"Parsed {len(readings)} HealthKit readings")
            
        except ET.ParseError as e:
            logger.error("Failed to parse HealthKit XML", error=str(e))
        
        return readings
    
    def _parse_record(self, record: ET.Element) -> DeviceReading | None:
        """Parse a single HealthKit Record element."""
        try:
            hk_type = record.get("type", "")
            metric_type = HEALTHKIT_TYPES.get(hk_type)
            
            if not metric_type:
                return None
            
            value_str = record.get("value", "0")
            try:
                value = float(value_str)
            except ValueError:
                return None
            
            timestamp_str = record.get("startDate", "")
            timestamp = self._parse_timestamp(timestamp_str)
            
            if not timestamp:
                return None
            
            return DeviceReading(
                metric_type=metric_type,
                value=value,
                unit=record.get("unit", ""),
                timestamp=timestamp,
                source_device=record.get("sourceName", "Apple Health"),
                source_platform=self.platform_name,
                metadata={
                    "hk_type": hk_type,
                    "end_date": record.get("endDate"),
                    "device": record.get("device"),
                },
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse record: {e}")
            return None
    
    def _parse_timestamp(self, ts: str) -> datetime | None:
        """Parse HealthKit timestamp format."""
        formats = [
            "%Y-%m-%d %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        
        return None
