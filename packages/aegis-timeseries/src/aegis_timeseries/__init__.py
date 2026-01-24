"""AEGIS Time-Series Database - Vitals, labs, trends"""
from aegis_timeseries.client import TimeSeriesClient
from aegis_timeseries.models import Vital, LabResult, WearableMetric
from aegis_timeseries.trends import TrendAnalyzer

__version__ = "0.1.0"
__all__ = ["TimeSeriesClient", "Vital", "LabResult", "WearableMetric", "TrendAnalyzer"]
