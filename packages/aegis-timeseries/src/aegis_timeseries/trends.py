"""Trend Analysis for Clinical Time-Series"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import structlog

from aegis_timeseries.client import TimeSeriesClient, TimeSeriesPoint
from aegis_timeseries.models import TimeSeriesQuery

logger = structlog.get_logger(__name__)


class TrendDirection(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TrendResult:
    metric_type: str
    direction: TrendDirection
    slope: float
    start_value: float
    end_value: float
    percent_change: float
    data_points: int


@dataclass
class ClinicalAlert:
    patient_id: str
    metric_type: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold: float
    timestamp: datetime


class TrendAnalyzer:
    """Analyze trends in clinical time-series data."""
    
    # Clinical thresholds for alerts
    VITAL_THRESHOLDS = {
        "heart_rate": {"low": 50, "high": 100, "critical_low": 40, "critical_high": 120},
        "bp_systolic": {"low": 90, "high": 140, "critical_low": 80, "critical_high": 180},
        "bp_diastolic": {"low": 60, "high": 90, "critical_low": 50, "critical_high": 120},
        "spo2": {"low": 92, "critical_low": 88},
        "temperature": {"low": 36.0, "high": 38.0, "critical_high": 39.5},
        "respiratory_rate": {"low": 12, "high": 20, "critical_high": 30},
    }
    
    LAB_THRESHOLDS = {
        "creatinine": {"high": 1.2, "critical_high": 4.0},
        "potassium": {"low": 3.5, "high": 5.0, "critical_low": 3.0, "critical_high": 6.0},
        "glucose": {"low": 70, "high": 200, "critical_low": 50, "critical_high": 400},
        "hemoglobin": {"low": 12.0, "critical_low": 7.0},
    }
    
    def __init__(self, client: TimeSeriesClient):
        self.client = client
    
    async def analyze_trend(self, patient_id: str, metric_type: str,
                           days: int = 7) -> TrendResult | None:
        """Analyze trend for a specific metric."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        query = TimeSeriesQuery(
            patient_id=patient_id,
            metric_types=[metric_type],
            start_time=start_time,
            end_time=end_time
        )
        points = await self.client.query_vitals(query)
        
        if len(points) < 2:
            return None
        
        # Calculate trend
        values = [p.value for p in points]
        start_val = values[0]
        end_val = values[-1]
        
        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine direction
        pct_change = ((end_val - start_val) / start_val * 100) if start_val != 0 else 0
        if abs(pct_change) < 5:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
        
        return TrendResult(
            metric_type=metric_type,
            direction=direction,
            slope=slope,
            start_value=start_val,
            end_value=end_val,
            percent_change=pct_change,
            data_points=n
        )
    
    async def check_alerts(self, patient_id: str, metric_type: str,
                          value: float) -> list[ClinicalAlert]:
        """Check if a value triggers clinical alerts."""
        alerts = []
        thresholds = self.VITAL_THRESHOLDS.get(metric_type) or self.LAB_THRESHOLDS.get(metric_type)
        
        if not thresholds:
            return alerts
        
        now = datetime.utcnow()
        
        # Check critical thresholds
        if "critical_high" in thresholds and value >= thresholds["critical_high"]:
            alerts.append(ClinicalAlert(
                patient_id=patient_id, metric_type=metric_type,
                severity=AlertSeverity.CRITICAL,
                message=f"CRITICAL: {metric_type} is critically high at {value}",
                current_value=value, threshold=thresholds["critical_high"], timestamp=now))
        elif "critical_low" in thresholds and value <= thresholds["critical_low"]:
            alerts.append(ClinicalAlert(
                patient_id=patient_id, metric_type=metric_type,
                severity=AlertSeverity.CRITICAL,
                message=f"CRITICAL: {metric_type} is critically low at {value}",
                current_value=value, threshold=thresholds["critical_low"], timestamp=now))
        # Check warning thresholds
        elif "high" in thresholds and value >= thresholds["high"]:
            alerts.append(ClinicalAlert(
                patient_id=patient_id, metric_type=metric_type,
                severity=AlertSeverity.WARNING,
                message=f"WARNING: {metric_type} is elevated at {value}",
                current_value=value, threshold=thresholds["high"], timestamp=now))
        elif "low" in thresholds and value <= thresholds["low"]:
            alerts.append(ClinicalAlert(
                patient_id=patient_id, metric_type=metric_type,
                severity=AlertSeverity.WARNING,
                message=f"WARNING: {metric_type} is low at {value}",
                current_value=value, threshold=thresholds["low"], timestamp=now))
        
        return alerts
    
    async def detect_deterioration(self, patient_id: str, hours: int = 24) -> list[ClinicalAlert]:
        """Detect clinical deterioration patterns."""
        alerts = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Check multiple vitals for deterioration patterns
        vitals_to_check = ["heart_rate", "bp_systolic", "spo2", "respiratory_rate"]
        
        concerning_trends = 0
        for vital in vitals_to_check:
            trend = await self.analyze_trend(patient_id, vital, days=1)
            if trend:
                # Check for concerning patterns
                if vital == "spo2" and trend.direction == TrendDirection.DECREASING:
                    concerning_trends += 1
                elif vital == "heart_rate" and trend.direction == TrendDirection.INCREASING:
                    concerning_trends += 1
                elif vital == "respiratory_rate" and trend.direction == TrendDirection.INCREASING:
                    concerning_trends += 1
        
        if concerning_trends >= 2:
            alerts.append(ClinicalAlert(
                patient_id=patient_id, metric_type="composite",
                severity=AlertSeverity.WARNING,
                message=f"Possible clinical deterioration: {concerning_trends} vital signs trending adversely",
                current_value=concerning_trends, threshold=2, timestamp=datetime.utcnow()))
        
        return alerts
