"""Incident Response - HITRUST 11.a"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import uuid
import structlog

logger = structlog.get_logger(__name__)


class IncidentType(str, Enum):
    BREACH = "breach"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_LOSS = "data_loss"
    SYSTEM_COMPROMISE = "system_compromise"
    POLICY_VIOLATION = "policy_violation"
    AVAILABILITY = "availability"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IncidentAction:
    timestamp: datetime
    action: str
    actor: str
    notes: str = ""


@dataclass
class Incident:
    id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    title: str
    description: str
    status: IncidentStatus = IncidentStatus.OPEN
    detected_at: datetime = field(default_factory=datetime.utcnow)
    reported_by: str | None = None
    assigned_to: str | None = None
    affected_systems: list[str] = field(default_factory=list)
    affected_patients: list[str] = field(default_factory=list)
    actions: list[IncidentAction] = field(default_factory=list)
    root_cause: str | None = None
    resolution: str | None = None
    resolved_at: datetime | None = None
    notification_required: bool = False
    notification_deadline: datetime | None = None


class IncidentManager:
    """
    Incident response management.
    
    HITRUST 11.a: Incident management responsibilities
    SOC 2 Availability: Incident response
    HIPAA: Breach notification (72 hours)
    """
    
    BREACH_NOTIFICATION_HOURS = 72
    
    def __init__(self, notification_callback=None):
        self._incidents: dict[str, Incident] = {}
        self._notify = notification_callback
    
    def create_incident(self, incident_type: IncidentType, severity: IncidentSeverity,
                       title: str, description: str, reporter: str,
                       affected_systems: list[str] | None = None,
                       affected_patients: list[str] | None = None) -> Incident:
        """Create a new security incident."""
        incident = Incident(
            id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            reported_by=reporter,
            affected_systems=affected_systems or [],
            affected_patients=affected_patients or []
        )
        
        # Check if breach notification required (HIPAA)
        if incident_type == IncidentType.BREACH and affected_patients:
            incident.notification_required = True
            incident.notification_deadline = datetime.utcnow() + timedelta(hours=self.BREACH_NOTIFICATION_HOURS)
        
        self._incidents[incident.id] = incident
        self._add_action(incident.id, "Incident created", reporter)
        
        logger.warning("Incident created",
            id=incident.id, type=incident_type.value, severity=severity.value)
        
        # Notify for critical incidents
        if severity == IncidentSeverity.CRITICAL and self._notify:
            self._notify(incident)
        
        return incident
    
    def update_status(self, incident_id: str, status: IncidentStatus, actor: str, notes: str = ""):
        """Update incident status."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return
        
        incident.status = status
        self._add_action(incident_id, f"Status changed to {status.value}", actor, notes)
        
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
    
    def assign(self, incident_id: str, assignee: str, actor: str):
        """Assign incident to a responder."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.assigned_to = assignee
            self._add_action(incident_id, f"Assigned to {assignee}", actor)
    
    def add_note(self, incident_id: str, note: str, actor: str):
        """Add a note to the incident."""
        self._add_action(incident_id, "Note added", actor, note)
    
    def set_root_cause(self, incident_id: str, root_cause: str, actor: str):
        """Set the root cause analysis."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.root_cause = root_cause
            self._add_action(incident_id, "Root cause identified", actor, root_cause)
    
    def resolve(self, incident_id: str, resolution: str, actor: str):
        """Resolve the incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.resolution = resolution
            incident.resolved_at = datetime.utcnow()
            incident.status = IncidentStatus.RESOLVED
            self._add_action(incident_id, "Incident resolved", actor, resolution)
    
    def get_open_incidents(self) -> list[Incident]:
        """Get all open incidents."""
        return [i for i in self._incidents.values() 
                if i.status not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]]
    
    def get_breaches_pending_notification(self) -> list[Incident]:
        """Get breaches requiring notification."""
        now = datetime.utcnow()
        return [i for i in self._incidents.values()
                if i.notification_required and i.notification_deadline
                and i.notification_deadline > now
                and i.status != IncidentStatus.CLOSED]
    
    def _add_action(self, incident_id: str, action: str, actor: str, notes: str = ""):
        incident = self._incidents.get(incident_id)
        if incident:
            incident.actions.append(IncidentAction(
                timestamp=datetime.utcnow(),
                action=action,
                actor=actor,
                notes=notes
            ))
