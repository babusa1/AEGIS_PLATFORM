"""
Devices & Wearables Domain Models

Models for medical devices and consumer wearables:
- Device (implants, equipment)
- DeviceMetric (real-time readings)
- WearableData (consumer health devices)

Critical for digital twin and real-time monitoring.

FHIR: Device, DeviceMetric, Observation
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class Device(BaseVertex):
    """
    Medical device (implant, equipment, monitor).
    
    FHIR: Device
    """
    
    _label = "Device"
    _fhir_resource_type = "Device"
    _omop_table = "device_exposure"
    
    # Identifiers
    udi: str | None = Field(default=None, description="Unique Device Identifier")
    serial_number: str | None = None
    lot_number: str | None = None
    
    # Device info
    manufacturer: str | None = None
    model_number: str | None = None
    device_name: str = Field(..., description="Device name")
    
    # Type
    type: Literal[
        "implant", "monitor", "pump", "ventilator",
        "wearable", "diagnostic", "therapeutic", "other"
    ] = Field(..., description="Device category")
    
    type_code: str | None = Field(default=None, description="SNOMED device type")
    
    # Status
    status: Literal["active", "inactive", "entered-in-error"] = "active"
    
    # For implants
    implant_date: datetime | None = None
    explant_date: datetime | None = None
    body_site: str | None = None
    
    # For connected devices
    is_connected: bool = Field(default=False, description="IoT connected")
    last_sync: datetime | None = None
    firmware_version: str | None = None
    
    # Relationships
    patient_id: str | None = Field(default=None, description="Patient if assigned")
    location_id: str | None = Field(default=None, description="Location if facility device")
    organization_id: str | None = None


class DeviceMetric(BaseVertex):
    """
    Real-time device metric/reading.
    
    FHIR: DeviceMetric, Observation
    """
    
    _label = "DeviceMetric"
    _fhir_resource_type = "DeviceMetric"
    _omop_table = "measurement"
    
    # Metric info
    metric_type: str = Field(..., description="Metric type (heart_rate, spo2, etc.)")
    metric_code: str | None = Field(default=None, description="MDC or LOINC code")
    
    # Value
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit of measure")
    
    # Quality
    category: Literal["measurement", "setting", "calculation", "unspecified"] = "measurement"
    operational_status: Literal["on", "off", "standby", "entered-in-error"] | None = None
    
    # Timing
    measurement_datetime: datetime = Field(..., description="When measured")
    
    # Calibration
    calibration_state: Literal["not_calibrated", "calibration_required", "calibrated"] | None = None
    
    # Relationships
    device_id: str = Field(..., description="Source device vertex ID")
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None


class WearableData(BaseVertex):
    """
    Consumer wearable/health app data.
    
    Aggregated data from Apple Watch, Fitbit, Garmin, etc.
    
    FHIR: Observation
    """
    
    _label = "WearableData"
    _fhir_resource_type = "Observation"
    _omop_table = "measurement"
    
    # Source
    source_app: str = Field(..., description="Source app (Apple Health, Fitbit, etc.)")
    device_type: Literal[
        "smartwatch", "fitness_tracker", "cgm", 
        "blood_pressure", "scale", "pulse_ox", "other"
    ] = Field(..., description="Device type")
    
    # Metric
    metric_type: Literal[
        "steps", "heart_rate", "heart_rate_variability",
        "sleep", "activity", "spo2", "respiratory_rate",
        "blood_glucose", "blood_pressure", "weight",
        "body_temperature", "ecg", "afib_detection", "other"
    ] = Field(..., description="Metric type")
    
    # Value (flexible for different types)
    value_numeric: float | None = None
    value_string: str | None = None
    unit: str | None = None
    
    # For complex metrics
    systolic: float | None = None  # BP
    diastolic: float | None = None  # BP
    sleep_minutes: int | None = None
    sleep_quality: str | None = None
    
    # Time period
    period_start: datetime = Field(..., description="Measurement period start")
    period_end: datetime | None = None
    
    # Data quality
    is_manual_entry: bool = Field(default=False, description="Manually entered vs device")
    confidence: float | None = Field(default=None, description="Data confidence 0-1")
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    device_id: str | None = Field(default=None, description="Device if tracked")


class DeviceAssociation(BaseVertex):
    """
    Association between device and patient/location.
    
    Tracks device assignments over time.
    """
    
    _label = "DeviceAssociation"
    _fhir_resource_type = "DeviceAssociation"
    _omop_table = None
    
    # Status
    status: Literal["implanted", "explanted", "attached", "removed", "entered-in-error"] = "attached"
    
    # Period
    period_start: datetime = Field(..., description="Association start")
    period_end: datetime | None = None
    
    # Body site (for implants/attached devices)
    body_site: str | None = None
    
    # Relationships
    device_id: str = Field(..., description="Device vertex ID")
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
