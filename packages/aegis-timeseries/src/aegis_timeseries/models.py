"""Time-Series Data Models"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class VitalType(str, Enum):
    HEART_RATE = "heart_rate"
    BP_SYSTOLIC = "bp_systolic"
    BP_DIASTOLIC = "bp_diastolic"
    TEMPERATURE = "temperature"
    RESPIRATORY_RATE = "respiratory_rate"
    SPO2 = "spo2"
    WEIGHT = "weight"


class LabCategory(str, Enum):
    CHEMISTRY = "chemistry"
    HEMATOLOGY = "hematology"
    COAGULATION = "coagulation"


@dataclass
class Vital:
    patient_id: str
    vital_type: VitalType
    value: float
    unit: str
    timestamp: datetime
    source: str = "ehr"
    tenant_id: str | None = None


@dataclass
class LabResult:
    patient_id: str
    test_code: str
    test_name: str
    value: float
    unit: str
    timestamp: datetime
    reference_low: float | None = None
    reference_high: float | None = None
    abnormal: bool = False
    tenant_id: str | None = None


@dataclass
class WearableMetric:
    patient_id: str
    metric_type: str
    value: float
    unit: str
    timestamp: datetime
    device_type: str
    tenant_id: str | None = None


@dataclass
class TimeSeriesQuery:
    patient_id: str
    metric_types: list[str] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    aggregation: str | None = None
    interval: str | None = None
