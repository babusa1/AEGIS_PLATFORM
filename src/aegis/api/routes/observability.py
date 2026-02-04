"""
Observability API Routes

Endpoints for:
- Metrics
- Traces
- Logs
- Alerts
- Dashboard
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aegis.observability import (
    get_tracer,
    get_metrics_collector,
    ObservabilityDashboard,
)
from aegis.observability.logging import get_logger, LogLevel
from aegis.observability.dashboard import AlertRule, AlertSeverity

router = APIRouter(prefix="/observability", tags=["observability"])

# Initialize dashboard
_dashboard = ObservabilityDashboard()


# =============================================================================
# Health & Status
# =============================================================================

@router.get("/health")
async def get_health():
    """Get overall system health status."""
    return _dashboard.get_health_status()


@router.get("/status")
async def get_status():
    """Get system status summary."""
    return {
        "metrics": _dashboard.get_metrics_summary(),
        "active_alerts": len(_dashboard.get_active_alerts()),
        "log_stats": _dashboard.get_log_stats(),
    }


# =============================================================================
# Metrics
# =============================================================================

@router.get("/metrics")
async def get_metrics(format: str = Query("json", enum=["json", "prometheus"])):
    """Get all metrics."""
    collector = get_metrics_collector()
    
    if format == "prometheus":
        return collector.to_prometheus()
    
    return collector.to_json()


@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get metrics summary for dashboard."""
    return _dashboard.get_metrics_summary()


@router.get("/metrics/{metric_name}")
async def get_metric(metric_name: str):
    """Get a specific metric value."""
    value = _dashboard.get_metric_value(metric_name)
    return {"metric": metric_name, "value": value}


# =============================================================================
# Traces
# =============================================================================

@router.get("/traces")
async def get_traces(limit: int = Query(50, le=200)):
    """Get recent traces."""
    return _dashboard.get_recent_traces(limit)


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get detailed trace view."""
    result = _dashboard.get_trace_detail(trace_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# =============================================================================
# Logs
# =============================================================================

class LogQuery(BaseModel):
    level: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100


@router.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    """Get recent logs."""
    log_level = None
    if level:
        try:
            log_level = LogLevel(level.lower())
        except ValueError:
            pass
    
    return _dashboard.get_recent_logs(log_level, limit, search)


@router.get("/logs/stats")
async def get_log_stats():
    """Get log statistics."""
    return _dashboard.get_log_stats()


# =============================================================================
# Alerts
# =============================================================================

@router.get("/alerts")
async def get_active_alerts():
    """Get active alerts."""
    return [a.dict() for a in _dashboard.get_active_alerts()]


@router.get("/alerts/history")
async def get_alert_history(limit: int = Query(100, le=500)):
    """Get alert history."""
    return [a.dict() for a in _dashboard.get_alert_history(limit)]


@router.get("/alerts/rules")
async def get_alert_rules():
    """Get all alert rules."""
    return [r.dict() for r in _dashboard.get_alert_rules()]


class AlertRuleCreate(BaseModel):
    id: str
    name: str
    description: str
    metric_name: str
    operator: str
    threshold: float
    severity: str = "warning"


@router.post("/alerts/rules")
async def create_alert_rule(rule: AlertRuleCreate):
    """Create a new alert rule."""
    alert_rule = AlertRule(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        metric_name=rule.metric_name,
        operator=rule.operator,
        threshold=rule.threshold,
        severity=AlertSeverity(rule.severity),
    )
    _dashboard.add_alert_rule(alert_rule)
    return {"status": "created", "rule_id": rule.id}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: str = Query(...)):
    """Acknowledge an alert."""
    success = _dashboard.acknowledge_alert(alert_id, user)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged"}


@router.post("/alerts/check")
async def check_alerts():
    """Manually check all alert rules."""
    _dashboard.check_alerts()
    return {"status": "checked", "active_alerts": len(_dashboard.get_active_alerts())}


# =============================================================================
# Dashboard
# =============================================================================

@router.get("/dashboard")
async def get_dashboard(dashboard_id: str = "aegis-main"):
    """Get dashboard with all panel data."""
    return _dashboard.get_dashboard(dashboard_id)


@router.get("/dashboard/panels")
async def get_dashboard_panels():
    """Get available dashboard panels."""
    config = _dashboard._dashboards.get("aegis-main")
    if config:
        return [p.dict() for p in config.panels]
    return []
