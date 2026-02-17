"""
Observability Dashboard

Real-time monitoring dashboard with:
- Metrics visualization
- Trace viewer
- Log aggregation
- Alert management
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio

import structlog
from pydantic import BaseModel, Field

from aegis.observability.tracing import get_tracer, Span
from aegis.observability.metrics import get_metrics_collector
from aegis.observability.logging import get_logger, LogEntry, LogLevel

logger = structlog.get_logger(__name__)


# =============================================================================
# Alert Models
# =============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class AlertRule(BaseModel):
    """An alert rule definition."""
    id: str
    name: str
    description: str
    
    # Condition
    metric_name: str
    operator: str  # >, <, >=, <=, ==
    threshold: float
    duration_seconds: int = 60  # Must be true for this duration
    
    # Severity
    severity: AlertSeverity = AlertSeverity.WARNING
    
    # Labels to match
    labels: Dict[str, str] = Field(default_factory=dict)
    
    # Notification
    notify_channels: List[str] = Field(default_factory=list)  # slack, email, pager
    
    # Status
    enabled: bool = True


class Alert(BaseModel):
    """A triggered alert."""
    id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    rule_id: str
    rule_name: str
    
    # Status
    status: AlertStatus = AlertStatus.FIRING
    severity: AlertSeverity
    
    # Details
    message: str
    current_value: float
    threshold: float
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    # Labels
    labels: Dict[str, str] = Field(default_factory=dict)


# =============================================================================
# Dashboard Data Models
# =============================================================================

class TimeSeriesPoint(BaseModel):
    """A point in a time series."""
    timestamp: datetime
    value: float


class DashboardPanel(BaseModel):
    """A dashboard panel configuration."""
    id: str
    title: str
    type: str  # gauge, line_chart, bar_chart, table, stat
    metric_query: str  # Metric name or expression
    width: int = 6  # 1-12 grid units
    height: int = 4
    thresholds: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    id: str
    name: str
    description: str = ""
    panels: List[DashboardPanel] = Field(default_factory=list)
    refresh_seconds: int = 30


# =============================================================================
# Observability Dashboard
# =============================================================================

class ObservabilityDashboard:
    """
    Real-time observability dashboard.
    
    Features:
    - Metrics overview
    - Trace visualization
    - Log aggregation
    - Alert management
    - Custom dashboards
    """
    
    def __init__(self):
        self.tracer = get_tracer()
        self.metrics = get_metrics_collector()
        self.logger = get_logger("dashboard")
        
        # Alert rules and active alerts
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        
        # Time series data (for charts)
        self._time_series: Dict[str, List[TimeSeriesPoint]] = {}
        self._max_points = 1000
        
        # Dashboards
        self._dashboards: Dict[str, DashboardConfig] = {}
        
        # Initialize default dashboard
        self._init_default_dashboard()
        
        # Initialize default alert rules
        self._init_default_alerts()
    
    def _init_default_dashboard(self):
        """Initialize the default VeritOS dashboard."""
        self._dashboards["aegis-main"] = DashboardConfig(
            id="aegis-main",
            name="VeritOS Orchestration Dashboard",
            description="Main monitoring dashboard for VeritOS",
            panels=[
                DashboardPanel(
                    id="active-workflows",
                    title="Active Workflows",
                    type="stat",
                    metric_query="aegis_active_workflows",
                    width=3,
                    height=2,
                ),
                DashboardPanel(
                    id="total-executions",
                    title="Total Executions",
                    type="stat",
                    metric_query="aegis_workflow_executions_total",
                    width=3,
                    height=2,
                ),
                DashboardPanel(
                    id="error-rate",
                    title="Error Rate",
                    type="gauge",
                    metric_query="aegis_workflow_errors_total / aegis_workflow_executions_total * 100",
                    width=3,
                    height=2,
                    thresholds=[
                        {"value": 0, "color": "green"},
                        {"value": 5, "color": "yellow"},
                        {"value": 10, "color": "red"},
                    ],
                ),
                DashboardPanel(
                    id="agent-cost",
                    title="Agent Cost ($)",
                    type="stat",
                    metric_query="aegis_agent_cost_dollars",
                    width=3,
                    height=2,
                ),
                DashboardPanel(
                    id="workflow-duration",
                    title="Workflow Duration (ms)",
                    type="line_chart",
                    metric_query="aegis_workflow_duration_seconds",
                    width=6,
                    height=4,
                ),
                DashboardPanel(
                    id="api-latency",
                    title="API Latency (ms)",
                    type="line_chart",
                    metric_query="aegis_api_latency_seconds",
                    width=6,
                    height=4,
                ),
                DashboardPanel(
                    id="recent-traces",
                    title="Recent Traces",
                    type="table",
                    metric_query="traces",
                    width=12,
                    height=4,
                ),
            ],
        )
    
    def _init_default_alerts(self):
        """Initialize default alert rules."""
        # High error rate
        self.add_alert_rule(AlertRule(
            id="high-error-rate",
            name="High Workflow Error Rate",
            description="Workflow error rate exceeds 10%",
            metric_name="workflow_error_rate",
            operator=">",
            threshold=10.0,
            severity=AlertSeverity.CRITICAL,
        ))
        
        # High latency
        self.add_alert_rule(AlertRule(
            id="high-latency",
            name="High API Latency",
            description="API P99 latency exceeds 5 seconds",
            metric_name="aegis_api_latency_seconds_p99",
            operator=">",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
        ))
        
        # High agent cost
        self.add_alert_rule(AlertRule(
            id="high-agent-cost",
            name="High Agent Cost",
            description="Agent cost exceeds $100",
            metric_name="aegis_agent_cost_dollars",
            operator=">",
            threshold=100.0,
            severity=AlertSeverity.WARNING,
        ))
    
    # =========================================================================
    # Metrics
    # =========================================================================
    
    def get_metrics_summary(self) -> dict:
        """Get metrics summary for dashboard."""
        return self.metrics.get_summary()
    
    def get_metric_value(self, metric_name: str, labels: Dict[str, str] = None) -> float:
        """Get current value of a metric."""
        metric = self.metrics._metrics.get(metric_name)
        if metric:
            return metric.get(labels)
        return 0.0
    
    def record_time_series(self, metric_name: str, value: float):
        """Record a time series data point."""
        if metric_name not in self._time_series:
            self._time_series[metric_name] = []
        
        self._time_series[metric_name].append(TimeSeriesPoint(
            timestamp=datetime.utcnow(),
            value=value,
        ))
        
        # Limit points
        if len(self._time_series[metric_name]) > self._max_points:
            self._time_series[metric_name] = self._time_series[metric_name][-self._max_points:]
    
    def get_time_series(
        self,
        metric_name: str,
        duration: timedelta = None,
    ) -> List[TimeSeriesPoint]:
        """Get time series data for a metric."""
        points = self._time_series.get(metric_name, [])
        
        if duration:
            cutoff = datetime.utcnow() - duration
            points = [p for p in points if p.timestamp >= cutoff]
        
        return points
    
    # =========================================================================
    # Traces
    # =========================================================================
    
    def get_recent_traces(self, limit: int = 50) -> List[dict]:
        """Get recent traces for dashboard."""
        return self.tracer.get_recent_traces(limit)
    
    def get_trace_detail(self, trace_id: str) -> dict:
        """Get detailed trace view."""
        spans = self.tracer.get_trace(trace_id)
        
        if not spans:
            return {"error": "Trace not found"}
        
        # Build trace tree
        root_span = next((s for s in spans if not s.parent_span_id), spans[0])
        
        def build_tree(span: Span) -> dict:
            children = [s for s in spans if s.parent_span_id == span.span_id]
            return {
                "span_id": span.span_id,
                "name": span.name,
                "kind": span.kind.value,
                "status": span.status.value,
                "duration_ms": span.duration_ms,
                "attributes": span.attributes,
                "events": span.events,
                "children": [build_tree(c) for c in children],
            }
        
        return {
            "trace_id": trace_id,
            "root_span": build_tree(root_span),
            "span_count": len(spans),
            "total_duration_ms": root_span.duration_ms,
            "start_time": root_span.start_time.isoformat(),
        }
    
    # =========================================================================
    # Logs
    # =========================================================================
    
    def get_recent_logs(
        self,
        level: LogLevel = None,
        limit: int = 100,
        search: str = None,
    ) -> List[dict]:
        """Get recent logs for dashboard."""
        if search:
            logs = self.logger.search_logs(search, limit)
        else:
            logs = self.logger.get_recent_logs(level, limit)
        
        return [log.dict() for log in logs]
    
    def get_log_stats(self) -> dict:
        """Get log statistics."""
        logs = self.logger._buffer
        
        by_level = {}
        for level in LogLevel:
            by_level[level.value] = len([l for l in logs if l.level == level])
        
        return {
            "total": len(logs),
            "by_level": by_level,
            "recent_errors": len([l for l in logs[-100:] if l.level in [LogLevel.ERROR, LogLevel.CRITICAL]]),
        }
    
    # =========================================================================
    # Alerts
    # =========================================================================
    
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self._alert_rules[rule.id] = rule
    
    def remove_alert_rule(self, rule_id: str):
        """Remove an alert rule."""
        self._alert_rules.pop(rule_id, None)
    
    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self._alert_rules.values())
    
    def check_alerts(self):
        """Check all alert rules and fire/resolve alerts."""
        for rule in self._alert_rules.values():
            if not rule.enabled:
                continue
            
            # Get metric value
            value = self.get_metric_value(rule.metric_name, rule.labels)
            
            # Check condition
            triggered = False
            if rule.operator == ">":
                triggered = value > rule.threshold
            elif rule.operator == "<":
                triggered = value < rule.threshold
            elif rule.operator == ">=":
                triggered = value >= rule.threshold
            elif rule.operator == "<=":
                triggered = value <= rule.threshold
            elif rule.operator == "==":
                triggered = value == rule.threshold
            
            # Handle alert state
            if triggered and rule.id not in self._active_alerts:
                # Fire new alert
                alert = Alert(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: {value} {rule.operator} {rule.threshold}",
                    current_value=value,
                    threshold=rule.threshold,
                    labels=rule.labels,
                )
                self._active_alerts[rule.id] = alert
                self._alert_history.append(alert)
                
                self.logger.warning(
                    f"Alert fired: {rule.name}",
                    alert_id=alert.id,
                    value=value,
                    threshold=rule.threshold,
                )
                
            elif not triggered and rule.id in self._active_alerts:
                # Resolve alert
                alert = self._active_alerts.pop(rule.id)
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                
                self.logger.info(
                    f"Alert resolved: {rule.name}",
                    alert_id=alert.id,
                )
    
    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self._alert_history[-limit:]
    
    def acknowledge_alert(self, alert_id: str, user: str):
        """Acknowledge an alert."""
        for alert in self._active_alerts.values():
            if alert.id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = user
                return True
        return False
    
    # =========================================================================
    # Dashboard
    # =========================================================================
    
    def get_dashboard(self, dashboard_id: str = "aegis-main") -> dict:
        """Get dashboard with all panel data."""
        config = self._dashboards.get(dashboard_id)
        if not config:
            return {"error": "Dashboard not found"}
        
        panels_data = []
        for panel in config.panels:
            panel_data = {
                "id": panel.id,
                "title": panel.title,
                "type": panel.type,
                "width": panel.width,
                "height": panel.height,
                "thresholds": panel.thresholds,
            }
            
            # Get data based on panel type
            if panel.type == "stat":
                panel_data["value"] = self.get_metric_value(panel.metric_query)
            elif panel.type == "gauge":
                panel_data["value"] = self.get_metric_value(panel.metric_query)
            elif panel.type == "line_chart":
                panel_data["data"] = [
                    {"x": p.timestamp.isoformat(), "y": p.value}
                    for p in self.get_time_series(panel.metric_query, timedelta(hours=1))
                ]
            elif panel.type == "table" and panel.metric_query == "traces":
                panel_data["data"] = self.get_recent_traces(10)
            
            panels_data.append(panel_data)
        
        return {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "refresh_seconds": config.refresh_seconds,
            "panels": panels_data,
            "active_alerts": len(self._active_alerts),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def get_health_status(self) -> dict:
        """Get overall system health status."""
        metrics = self.get_metrics_summary()
        active_alerts = self.get_active_alerts()
        
        # Determine overall status
        if any(a.severity == AlertSeverity.CRITICAL for a in active_alerts):
            status = "critical"
        elif any(a.severity == AlertSeverity.WARNING for a in active_alerts):
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "active_alerts": len(active_alerts),
            "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            "metrics": metrics,
            "uptime_seconds": 0,  # Would track actual uptime
            "last_check": datetime.utcnow().isoformat(),
        }
