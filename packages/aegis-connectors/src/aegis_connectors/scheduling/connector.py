"""Scheduling Connector"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult

logger = structlog.get_logger(__name__)

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    ARRIVED = "arrived"
    CHECKED_IN = "checked-in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no-show"

class AppointmentType(str, Enum):
    OFFICE_VISIT = "office-visit"
    FOLLOW_UP = "follow-up"
    NEW_PATIENT = "new-patient"
    PROCEDURE = "procedure"
    TELEHEALTH = "telehealth"
    LAB = "lab"
    IMAGING = "imaging"

@dataclass
class Appointment:
    appointment_id: str
    patient_id: str
    provider_id: str | None
    location_id: str | None
    appointment_type: AppointmentType
    status: AppointmentStatus
    start_time: datetime
    end_time: datetime | None
    reason: str | None = None
    notes: str | None = None
    cancellation_reason: str | None = None

class SchedulingConnector(BaseConnector):
    def __init__(self, tenant_id: str, source_system: str = "scheduling"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "scheduling"
    
    async def parse(self, data: Any) -> ConnectorResult:
        errors = []
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be dict"])
        try:
            appt = self._parse_appointment(data)
            if not appt:
                return ConnectorResult(success=False, errors=["Failed to parse"])
            vertices, edges = self._transform(appt)
            return ConnectorResult(success=True, vertices=vertices, edges=edges,
                metadata={"appointment_id": appt.appointment_id, "status": appt.status.value})
        except Exception as e:
            return ConnectorResult(success=False, errors=[str(e)])
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be dict")
        elif not data.get("patient_id"):
            errors.append("Missing patient_id")
        elif not data.get("start_time"):
            errors.append("Missing start_time")
        return errors
    
    def _parse_appointment(self, data: dict) -> Appointment | None:
        try:
            start = data.get("start_time", data.get("start"))
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end = data.get("end_time", data.get("end"))
            if isinstance(end, str):
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            status = AppointmentStatus(data.get("status", "scheduled"))
            appt_type = AppointmentType(data.get("appointment_type", data.get("type", "office-visit")))
            return Appointment(data.get("appointment_id", data.get("id", "")), data.get("patient_id", ""),
                data.get("provider_id"), data.get("location_id"), appt_type, status, start, end,
                data.get("reason"), data.get("notes"), data.get("cancellation_reason"))
        except Exception as e:
            logger.error("Appointment parse failed", error=str(e))
            return None
    
    def _transform(self, appt: Appointment):
        vertices, edges = [], []
        appt_id = f"Appointment/{appt.appointment_id}"
        vertices.append(self._create_vertex("Appointment", appt_id, {
            "appointment_id": appt.appointment_id, "appointment_type": appt.appointment_type.value,
            "status": appt.status.value, "start_time": appt.start_time.isoformat(),
            "end_time": appt.end_time.isoformat() if appt.end_time else None,
            "reason": appt.reason, "cancellation_reason": appt.cancellation_reason,
            "is_no_show": appt.status == AppointmentStatus.NO_SHOW}))
        edges.append(self._create_edge("HAS_APPOINTMENT", "Patient", f"Patient/{appt.patient_id}",
            "Appointment", appt_id))
        if appt.provider_id:
            edges.append(self._create_edge("SCHEDULED_WITH", "Appointment", appt_id,
                "Practitioner", f"Practitioner/{appt.provider_id}"))
        if appt.location_id:
            edges.append(self._create_edge("AT_LOCATION", "Appointment", appt_id,
                "Location", f"Location/{appt.location_id}"))
        return vertices, edges

SAMPLE_APPOINTMENT = {"appointment_id": "APPT-001", "patient_id": "PAT12345",
    "provider_id": "DR-001", "location_id": "LOC-001", "appointment_type": "follow-up",
    "status": "scheduled", "start_time": "2024-01-20T09:00:00", "end_time": "2024-01-20T09:30:00",
    "reason": "Diabetes follow-up"}
