"""Access Anomaly Detection - HITRUST 01.m"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class AnomalyType(str, Enum):
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_VOLUME = "unusual_volume"
    UNUSUAL_LOCATION = "unusual_location"
    UNUSUAL_PATTERN = "unusual_pattern"
    BULK_ACCESS = "bulk_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    id: str
    anomaly_type: AnomalyType
    severity: Severity
    user_id: str
    description: str
    detected_at: datetime
    evidence: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


@dataclass
class UserProfile:
    user_id: str
    typical_hours: tuple[int, int] = (8, 18)  # 8am-6pm
    typical_access_count: int = 50
    known_ips: list[str] = field(default_factory=list)
    accessed_patients: set[str] = field(default_factory=set)


class AnomalyDetector:
    """
    Detect anomalous access patterns.
    
    HITRUST 01.m: Monitoring and review of access
    SOC 2 Security: Unauthorized access detection
    """
    
    def __init__(self):
        self._profiles: dict[str, UserProfile] = {}
        self._access_log: list[dict] = []
        self._alerts: list[AnomalyAlert] = []
        self._alert_counter = 0
    
    def record_access(self, user_id: str, resource: str, patient_id: str | None,
                     ip_address: str | None, timestamp: datetime | None = None):
        """Record an access event for analysis."""
        ts = timestamp or datetime.utcnow()
        
        self._access_log.append({
            "user_id": user_id,
            "resource": resource,
            "patient_id": patient_id,
            "ip": ip_address,
            "timestamp": ts
        })
        
        # Update profile
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        
        profile = self._profiles[user_id]
        if patient_id:
            profile.accessed_patients.add(patient_id)
        if ip_address and ip_address not in profile.known_ips:
            profile.known_ips.append(ip_address)
        
        # Analyze for anomalies
        alerts = self._analyze_access(user_id, ts, ip_address, patient_id)
        self._alerts.extend(alerts)
        
        for alert in alerts:
            logger.warning("Anomaly detected", alert_id=alert.id, type=alert.anomaly_type.value)
    
    def _analyze_access(self, user_id: str, timestamp: datetime,
                       ip_address: str | None, patient_id: str | None) -> list[AnomalyAlert]:
        alerts = []
        profile = self._profiles.get(user_id)
        if not profile:
            return alerts
        
        # Check unusual time
        hour = timestamp.hour
        if hour < profile.typical_hours[0] or hour > profile.typical_hours[1]:
            alerts.append(self._create_alert(
                AnomalyType.UNUSUAL_TIME,
                Severity.MEDIUM,
                user_id,
                f"Access at unusual hour: {hour}:00",
                {"hour": hour, "typical": profile.typical_hours}
            ))
        
        # Check unusual volume (last hour)
        hour_ago = timestamp - timedelta(hours=1)
        recent = [a for a in self._access_log 
                 if a["user_id"] == user_id and a["timestamp"] > hour_ago]
        
        if len(recent) > profile.typical_access_count * 2:
            alerts.append(self._create_alert(
                AnomalyType.UNUSUAL_VOLUME,
                Severity.HIGH,
                user_id,
                f"High volume access: {len(recent)} in last hour",
                {"count": len(recent), "typical": profile.typical_access_count}
            ))
        
        # Check bulk patient access
        if patient_id:
            recent_patients = set(a["patient_id"] for a in recent if a["patient_id"])
            if len(recent_patients) > 20:
                alerts.append(self._create_alert(
                    AnomalyType.BULK_ACCESS,
                    Severity.HIGH,
                    user_id,
                    f"Bulk patient access: {len(recent_patients)} patients in 1 hour",
                    {"patient_count": len(recent_patients)}
                ))
        
        # Check unusual IP
        if ip_address and len(profile.known_ips) > 5 and ip_address not in profile.known_ips[:5]:
            alerts.append(self._create_alert(
                AnomalyType.UNUSUAL_LOCATION,
                Severity.MEDIUM,
                user_id,
                f"Access from new IP: {ip_address}",
                {"ip": ip_address}
            ))
        
        return alerts
    
    def _create_alert(self, atype: AnomalyType, severity: Severity,
                     user_id: str, description: str, evidence: dict) -> AnomalyAlert:
        self._alert_counter += 1
        return AnomalyAlert(
            id=f"ANOM-{self._alert_counter:06d}",
            anomaly_type=atype,
            severity=severity,
            user_id=user_id,
            description=description,
            detected_at=datetime.utcnow(),
            evidence=evidence
        )
    
    def get_alerts(self, severity: Severity | None = None,
                  acknowledged: bool | None = None) -> list[AnomalyAlert]:
        """Get alerts filtered by criteria."""
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        return alerts
    
    def acknowledge_alert(self, alert_id: str, reviewer: str):
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                break
