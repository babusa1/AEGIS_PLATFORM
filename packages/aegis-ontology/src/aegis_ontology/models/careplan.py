"""
Care Planning Domain Models

Models for care coordination:
- CarePlan (treatment plans)
- Goal (patient goals)
- CareTeam (care team members)
- Task (clinical tasks)
- ServiceRequest (orders, referrals)

FHIR: CarePlan, Goal, CareTeam, Task, ServiceRequest
"""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class CarePlan(BaseVertex):
    """
    Care plan / treatment plan.
    
    FHIR: CarePlan
    """
    
    _label = "CarePlan"
    _fhir_resource_type = "CarePlan"
    _omop_table = None
    
    # Status
    status: Literal[
        "draft", "active", "on-hold", "revoked",
        "completed", "entered-in-error"
    ] = "active"
    
    intent: Literal["proposal", "plan", "order", "option"] = "plan"
    
    # Category
    category: str | None = Field(default=None, description="Care plan type")
    
    # Title/Description
    title: str = Field(..., description="Care plan title")
    description: str | None = None
    
    # Period
    period_start: date | None = None
    period_end: date | None = None
    
    # Conditions addressed
    addresses_conditions: list[str] | None = Field(
        default=None, description="Condition IDs addressed"
    )
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    author_id: str | None = Field(default=None, description="Author provider")
    care_team_id: str | None = None
    
    # Activities
    activity_count: int | None = None


class Goal(BaseVertex):
    """
    Patient goal.
    
    FHIR: Goal
    """
    
    _label = "Goal"
    _fhir_resource_type = "Goal"
    _omop_table = None
    
    # Lifecycle
    lifecycle_status: Literal[
        "proposed", "planned", "accepted", "active",
        "on-hold", "completed", "cancelled", "entered-in-error", "rejected"
    ] = "active"
    
    # Achievement
    achievement_status: Literal[
        "in-progress", "improving", "worsening", "no-change",
        "achieved", "sustaining", "not-achieved", "no-progress", "not-attainable"
    ] | None = None
    
    # Priority
    priority: Literal["high", "medium", "low"] | None = None
    
    # Description
    description: str = Field(..., description="Goal description")
    
    # Target
    target_measure: str | None = Field(default=None, description="Target metric")
    target_value: str | None = None
    target_date: date | None = None
    
    # Dates
    start_date: date | None = None
    status_date: date | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    care_plan_id: str | None = None
    expressed_by_id: str | None = Field(default=None, description="Who set the goal")


class CareTeam(BaseVertex):
    """
    Care team for a patient.
    
    FHIR: CareTeam
    """
    
    _label = "CareTeam"
    _fhir_resource_type = "CareTeam"
    _omop_table = None
    
    # Status
    status: Literal["proposed", "active", "suspended", "inactive", "entered-in-error"] = "active"
    
    # Category
    category: str | None = Field(default=None, description="Team type")
    
    # Name
    name: str | None = None
    
    # Period
    period_start: date | None = None
    period_end: date | None = None
    
    # Reason
    reason_code: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    managing_organization_id: str | None = None
    
    # Member count
    member_count: int | None = None


class CareTeamMember(BaseVertex):
    """
    Care team member assignment.
    
    FHIR: CareTeam.participant
    """
    
    _label = "CareTeamMember"
    _fhir_resource_type = "CareTeam"
    _omop_table = None
    
    # Role
    role: str = Field(..., description="Team member role")
    role_code: str | None = None
    
    # Period
    period_start: date | None = None
    period_end: date | None = None
    
    # Relationships
    care_team_id: str = Field(..., description="CareTeam vertex ID")
    member_id: str = Field(..., description="Provider/Patient vertex ID")
    member_type: Literal["Practitioner", "Patient", "RelatedPerson", "Organization"] = "Practitioner"


class Task(BaseVertex):
    """
    Clinical/administrative task.
    
    FHIR: Task
    """
    
    _label = "Task"
    _fhir_resource_type = "Task"
    _omop_table = None
    
    # Status
    status: Literal[
        "draft", "requested", "received", "accepted", "rejected",
        "ready", "cancelled", "in-progress", "on-hold", "failed",
        "completed", "entered-in-error"
    ] = "requested"
    
    intent: Literal["unknown", "proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"] = "order"
    
    # Priority
    priority: Literal["routine", "urgent", "asap", "stat"] = "routine"
    
    # Description
    code: str | None = Field(default=None, description="Task type code")
    description: str = Field(..., description="Task description")
    
    # Focus
    focus_type: str | None = Field(default=None, description="What task is about")
    focus_id: str | None = None
    
    # Timing
    authored_on: datetime | None = None
    last_modified: datetime | None = None
    execution_period_start: datetime | None = None
    execution_period_end: datetime | None = None
    
    # Due
    due_date: datetime | None = None
    
    # Relationships
    patient_id: str | None = Field(default=None, description="Patient if applicable")
    encounter_id: str | None = None
    requester_id: str | None = None
    owner_id: str | None = Field(default=None, description="Assigned to")
    
    # Notes
    note: str | None = None
    
    # Output
    output_value: str | None = None


class ServiceRequest(BaseVertex):
    """
    Service request (order, referral).
    
    FHIR: ServiceRequest
    """
    
    _label = "ServiceRequest"
    _fhir_resource_type = "ServiceRequest"
    _omop_table = None
    
    # Status
    status: Literal[
        "draft", "active", "on-hold", "revoked",
        "completed", "entered-in-error"
    ] = "active"
    
    intent: Literal["proposal", "plan", "directive", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"] = "order"
    
    # Category
    category: str | None = Field(default=None, description="Service category")
    
    # Priority
    priority: Literal["routine", "urgent", "asap", "stat"] = "routine"
    
    # Service
    code: str = Field(..., description="Service code")
    code_display: str | None = None
    
    # Quantity
    quantity_value: float | None = None
    quantity_unit: str | None = None
    
    # Timing
    occurrence_datetime: datetime | None = None
    authored_on: datetime | None = None
    
    # Reason
    reason_code: str | None = None
    reason_display: str | None = None
    
    # Body site
    body_site: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    requester_id: str | None = None
    performer_id: str | None = None
    
    # Notes
    note: str | None = None


class Referral(BaseVertex):
    """
    Referral to specialist/facility.
    
    FHIR: ServiceRequest (referral intent)
    """
    
    _label = "Referral"
    _fhir_resource_type = "ServiceRequest"
    _omop_table = None
    
    # Status
    status: Literal[
        "draft", "active", "on-hold", "revoked",
        "completed", "entered-in-error"
    ] = "active"
    
    # Type
    referral_type: str = Field(..., description="Referral type/specialty")
    
    # Priority
    priority: Literal["routine", "urgent", "asap", "stat"] = "routine"
    
    # Reason
    reason: str = Field(..., description="Referral reason")
    diagnosis_codes: list[str] | None = None
    
    # Timing
    authored_on: datetime | None = None
    validity_period_start: date | None = None
    validity_period_end: date | None = None
    
    # Authorization
    auth_required: bool = False
    authorization_id: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    referring_provider_id: str | None = None
    referred_to_provider_id: str | None = None
    referred_to_organization_id: str | None = None
    
    # Notes
    note: str | None = None
