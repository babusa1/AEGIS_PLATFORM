"""
Communication & Scheduling Domain Models

FHIR: Communication, Appointment, Schedule
"""

from datetime import datetime, date
from typing import Literal
from pydantic import Field
from aegis_ontology.models.base import BaseVertex


class Communication(BaseVertex):
    """Message/notification. FHIR: Communication"""
    
    _label = "Communication"
    _fhir_resource_type = "Communication"
    _omop_table = None
    
    status: Literal["in-progress", "completed", "entered-in-error"] = "completed"
    category: Literal["alert", "notification", "reminder", "message", "other"] = "message"
    medium: Literal["email", "sms", "phone", "portal", "app", "other"] = Field(...)
    direction: Literal["inbound", "outbound"] = "outbound"
    subject: str | None = None
    content: str = Field(...)
    sent_datetime: datetime | None = None
    delivery_status: Literal["sent", "delivered", "failed", "read"] | None = None
    patient_id: str = Field(...)
    sender_id: str | None = None
    is_ai_generated: bool = False


class Appointment(BaseVertex):
    """Scheduled appointment. FHIR: Appointment"""
    
    _label = "Appointment"
    _fhir_resource_type = "Appointment"
    _omop_table = "visit_occurrence"
    
    status: Literal["proposed", "booked", "arrived", "fulfilled", "cancelled", "noshow"] = "booked"
    appointment_type: str = Field(...)
    description: str | None = None
    start_datetime: datetime = Field(...)
    end_datetime: datetime | None = None
    minutes_duration: int | None = None
    is_virtual: bool = False
    reason_code: str | None = None
    patient_id: str = Field(...)
    provider_id: str | None = None
    location_id: str | None = None
    encounter_id: str | None = None


class Schedule(BaseVertex):
    """Provider schedule. FHIR: Schedule"""
    
    _label = "Schedule"
    _fhir_resource_type = "Schedule"
    _omop_table = None
    
    active: bool = True
    service_type: str | None = None
    specialty: str | None = None
    provider_id: str | None = None
    location_id: str | None = None


class Slot(BaseVertex):
    """Appointment slot. FHIR: Slot"""
    
    _label = "Slot"
    _fhir_resource_type = "Slot"
    _omop_table = None
    
    status: Literal["busy", "free", "busy-unavailable"] = "free"
    start_datetime: datetime = Field(...)
    end_datetime: datetime = Field(...)
    schedule_id: str = Field(...)


class PatientEngagement(BaseVertex):
    """Patient engagement metrics."""
    
    _label = "PatientEngagement"
    _fhir_resource_type = None
    _omop_table = None
    
    period_start: date = Field(...)
    app_sessions: int | None = None
    last_app_login: datetime | None = None
    messages_sent: int | None = None
    appointments_attended: int | None = None
    engagement_score: float | None = None
    patient_id: str = Field(...)
