"""
Metrics Collection

Features:
- Counters, Histograms, Gauges
- Labels/dimensions
- Prometheus-compatible
- Real-time aggregation
"""

from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import threading
import time
import json

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Metric Types
# =============================================================================

class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricValue(BaseModel):
    """A metric data point."""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Counter
# =============================================================================

class Counter:
    """
    A monotonically increasing counter.
    
    Usage:
        request_count = Counter("http_requests_total", "Total HTTP requests")
        request_count.inc()
        request_count.inc(labels={"method": "GET", "status": "200"})
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment the counter."""
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] += value
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        key = self._labels_key(labels)
        return self._values.get(key, 0.0)
    
    def _labels_key(self, labels: Dict[str, str] = None) -> str:
        """Create a key from labels."""
        if not labels:
            return ""
        return json.dumps(labels, sort_keys=True)
    
    def collect(self) -> List[MetricValue]:
        """Collect all metric values."""
        values = []
        for key, value in self._values.items():
            labels = json.loads(key) if key else {}
            values.append(MetricValue(
                name=self.name,
                type=MetricType.COUNTER,
                value=value,
                labels=labels,
            ))
        return values


# =============================================================================
# Gauge
# =============================================================================

class Gauge:
    """
    A metric that can go up and down.
    
    Usage:
        temperature = Gauge("temperature_celsius", "Current temperature")
        temperature.set(23.5)
        temperature.inc(0.5)
        temperature.dec(1.0)
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: Dict[str, str] = None):
        """Set the gauge value."""
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment the gauge."""
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] += value
    
    def dec(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Decrement the gauge."""
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] -= value
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current gauge value."""
        key = self._labels_key(labels)
        return self._values.get(key, 0.0)
    
    def _labels_key(self, labels: Dict[str, str] = None) -> str:
        if not labels:
            return ""
        return json.dumps(labels, sort_keys=True)
    
    def collect(self) -> List[MetricValue]:
        """Collect all metric values."""
        values = []
        for key, value in self._values.items():
            labels = json.loads(key) if key else {}
            values.append(MetricValue(
                name=self.name,
                type=MetricType.GAUGE,
                value=value,
                labels=labels,
            ))
        return values


# =============================================================================
# Histogram
# =============================================================================

class Histogram:
    """
    A metric that tracks value distributions.
    
    Usage:
        request_duration = Histogram(
            "http_request_duration_seconds",
            "Request duration",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        request_duration.observe(0.25)
    """
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    
    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: List[float] = None,
    ):
        self.name = name
        self.description = description
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        
        self._lock = threading.Lock()
        # Per-label histograms: label_key -> {bucket -> count, sum, count}
        self._data: Dict[str, Dict] = defaultdict(lambda: {
            "buckets": {b: 0 for b in self.buckets},
            "sum": 0.0,
            "count": 0,
        })
    
    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe a value."""
        key = self._labels_key(labels)
        with self._lock:
            data = self._data[key]
            data["sum"] += value
            data["count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    data["buckets"][bucket] += 1
    
    def get_percentile(self, percentile: float, labels: Dict[str, str] = None) -> float:
        """Estimate a percentile from the histogram."""
        key = self._labels_key(labels)
        data = self._data.get(key)
        if not data or data["count"] == 0:
            return 0.0
        
        target = data["count"] * (percentile / 100.0)
        cumulative = 0
        prev_bucket = 0
        
        for bucket in self.buckets:
            cumulative += data["buckets"][bucket]
            if cumulative >= target:
                # Linear interpolation within bucket
                return bucket
            prev_bucket = bucket
        
        return self.buckets[-1]
    
    def _labels_key(self, labels: Dict[str, str] = None) -> str:
        if not labels:
            return ""
        return json.dumps(labels, sort_keys=True)
    
    def collect(self) -> List[MetricValue]:
        """Collect all metric values."""
        values = []
        for key, data in self._data.items():
            labels = json.loads(key) if key else {}
            
            # Bucket values
            cumulative = 0
            for bucket in self.buckets:
                cumulative += data["buckets"][bucket]
                values.append(MetricValue(
                    name=f"{self.name}_bucket",
                    type=MetricType.HISTOGRAM,
                    value=cumulative,
                    labels={**labels, "le": str(bucket)},
                ))
            
            # +Inf bucket
            values.append(MetricValue(
                name=f"{self.name}_bucket",
                type=MetricType.HISTOGRAM,
                value=data["count"],
                labels={**labels, "le": "+Inf"},
            ))
            
            # Sum and count
            values.append(MetricValue(
                name=f"{self.name}_sum",
                type=MetricType.HISTOGRAM,
                value=data["sum"],
                labels=labels,
            ))
            values.append(MetricValue(
                name=f"{self.name}_count",
                type=MetricType.HISTOGRAM,
                value=data["count"],
                labels=labels,
            ))
        
        return values


# =============================================================================
# Metrics Collector
# =============================================================================

class MetricsCollector:
    """
    Central metrics collector.
    
    Manages all metrics and provides Prometheus-compatible output.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Built-in metrics
        self._init_builtin_metrics()
    
    def _init_builtin_metrics(self):
        """Initialize built-in metrics."""
        # Workflow metrics
        self.workflow_executions = self.counter(
            "aegis_workflow_executions_total",
            "Total workflow executions"
        )
        self.workflow_duration = self.histogram(
            "aegis_workflow_duration_seconds",
            "Workflow execution duration"
        )
        self.workflow_errors = self.counter(
            "aegis_workflow_errors_total",
            "Total workflow errors"
        )
        
        # Agent metrics
        self.agent_invocations = self.counter(
            "aegis_agent_invocations_total",
            "Total agent invocations"
        )
        self.agent_duration = self.histogram(
            "aegis_agent_duration_seconds",
            "Agent execution duration"
        )
        self.agent_tokens = self.counter(
            "aegis_agent_tokens_total",
            "Total tokens used by agents"
        )
        self.agent_cost = self.counter(
            "aegis_agent_cost_dollars",
            "Total cost of agent invocations"
        )
        
        # Data Moat metrics
        self.db_queries = self.counter(
            "aegis_db_queries_total",
            "Total database queries"
        )
        self.db_query_duration = self.histogram(
            "aegis_db_query_duration_seconds",
            "Database query duration"
        )
        
        # API metrics
        self.api_requests = self.counter(
            "aegis_api_requests_total",
            "Total API requests"
        )
        self.api_latency = self.histogram(
            "aegis_api_latency_seconds",
            "API request latency"
        )
        
        # Active resources
        self.active_workflows = self.gauge(
            "aegis_active_workflows",
            "Currently active workflows"
        )
        self.active_agents = self.gauge(
            "aegis_active_agents",
            "Currently active agents"
        )
    
    def counter(self, name: str, description: str = "") -> Counter:
        """Create or get a counter."""
        if name not in self._metrics:
            self._metrics[name] = Counter(name, description)
        return self._metrics[name]
    
    def gauge(self, name: str, description: str = "") -> Gauge:
        """Create or get a gauge."""
        if name not in self._metrics:
            self._metrics[name] = Gauge(name, description)
        return self._metrics[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: List[float] = None,
    ) -> Histogram:
        """Create or get a histogram."""
        if name not in self._metrics:
            self._metrics[name] = Histogram(name, description, buckets)
        return self._metrics[name]
    
    def collect_all(self) -> List[MetricValue]:
        """Collect all metrics."""
        values = []
        for metric in self._metrics.values():
            values.extend(metric.collect())
        return values
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, metric in self._metrics.items():
            # Add HELP and TYPE
            lines.append(f"# HELP {name} {metric.description}")
            
            if isinstance(metric, Counter):
                lines.append(f"# TYPE {name} counter")
            elif isinstance(metric, Gauge):
                lines.append(f"# TYPE {name} gauge")
            elif isinstance(metric, Histogram):
                lines.append(f"# TYPE {name} histogram")
            
            # Add values
            for value in metric.collect():
                if value.labels:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in value.labels.items())
                    lines.append(f"{value.name}{{{labels_str}}} {value.value}")
                else:
                    lines.append(f"{value.name} {value.value}")
        
        return "\n".join(lines)
    
    def to_json(self) -> dict:
        """Export metrics as JSON."""
        result = {}
        for value in self.collect_all():
            key = value.name
            if value.labels:
                key += "_" + "_".join(f"{k}_{v}" for k, v in value.labels.items())
            result[key] = {
                "value": value.value,
                "type": value.type.value,
                "labels": value.labels,
                "timestamp": value.timestamp.isoformat(),
            }
        return result
    
    def get_summary(self) -> dict:
        """Get a summary of key metrics."""
        return {
            "workflows": {
                "total": self.workflow_executions.get(),
                "errors": self.workflow_errors.get(),
                "active": self.active_workflows.get(),
                "avg_duration_ms": self.workflow_duration.get_percentile(50) * 1000,
                "p99_duration_ms": self.workflow_duration.get_percentile(99) * 1000,
            },
            "agents": {
                "total_invocations": self.agent_invocations.get(),
                "total_tokens": self.agent_tokens.get(),
                "total_cost": round(self.agent_cost.get(), 4),
                "active": self.active_agents.get(),
            },
            "database": {
                "total_queries": self.db_queries.get(),
                "avg_duration_ms": self.db_query_duration.get_percentile(50) * 1000,
            },
            "api": {
                "total_requests": self.api_requests.get(),
                "avg_latency_ms": self.api_latency.get_percentile(50) * 1000,
            },
        }


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
