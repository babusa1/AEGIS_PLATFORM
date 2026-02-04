"""
AEGIS Observability Module

Complete observability stack:
- OpenTelemetry for distributed tracing
- Metrics collection
- Logging aggregation
- Real-time monitoring
"""

from aegis.observability.tracing import Tracer, trace, trace_async
from aegis.observability.metrics import MetricsCollector, Counter, Histogram, Gauge
from aegis.observability.logging import StructuredLogger, LogLevel
from aegis.observability.dashboard import ObservabilityDashboard

__all__ = [
    "Tracer",
    "trace",
    "trace_async",
    "MetricsCollector",
    "Counter",
    "Histogram",
    "Gauge",
    "StructuredLogger",
    "LogLevel",
    "ObservabilityDashboard",
]
