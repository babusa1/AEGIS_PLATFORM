"""Entity Models - Pydantic models for all clinical entities"""
from datetime import datetime, date
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ConditionStatus(str, Enum):
    ACTIVE = "active"
    RECURRENCE = "recurrence"
    RELAPSE = "relapse"
    INACTIVE = "inactive"
    REMISSION = "remission"
    RESOLVED = "resolved"


class MedicationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"


class EncounterStatus(str, Enum):
    PLANNED = "planned"
    ARRIVED = "arrived"
    IN_PROGRESS = "in-progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class BaseEntity(BaseModel):
    """Base class for all entities."""
    id: str
    tenant_id: str
    source_system: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    
    class Config:
        use_enum_values = True


class Patient(BaseEntity):
    """Patient entity."""
    mrn: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    gender: Gender | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email: str | None = None
    deceased: bool = False
    deceased_date: date | None = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Condition(BaseEntity):
    """Clinical condition/diagnosis entity."""
    patient_id: str
    code: str
    code_system: str = "http://snomed.info/sct"
    display: str | None = None
    status: ConditionStatus = ConditionStatus.ACTIVE
    category: str | None = None  # problem-list, encounter-diagnosis
    onset_date: datetime | None = None
    abatement_date: datetime | None = None
    severity: str | None = None
    encounter_id: str | None = None


class Medication(BaseEntity):
    """Medication entity."""
    patient_id: str
    code: str | None = None
    code_system: str = "http://www.nlm.nih.gov/research/umls/rxnorm"
    display: str
    status: MedicationStatus = MedicationStatus.ACTIVE
    dosage: str | None = None
    dosage_value: float | None = None
    dosage_unit: str | None = None
    route: str | None = None
    frequency: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    prescriber_id: str | None = None
    encounter_id: str | None = None


class Encounter(BaseEntity):
    """Patient encounter/visit entity."""
    patient_id: str
    encounter_type: str | None = None  # ambulatory, inpatient, emergency
    status: EncounterStatus = EncounterStatus.FINISHED
    class_code: str | None = None  # AMB, IMP, EMER
    start_date: datetime
    end_date: datetime | None = None
    location_id: str | None = None
    location_name: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    reason: str | None = None
    discharge_disposition: str | None = None


class Observation(BaseEntity):
    """Clinical observation (lab, vital, etc)."""
    patient_id: str
    code: str
    code_system: str = "http://loinc.org"
    display: str | None = None
    category: str | None = None  # vital-signs, laboratory, social-history
    value_string: str | None = None
    value_numeric: float | None = None
    value_boolean: bool | None = None
    unit: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    interpretation: str | None = None  # normal, abnormal, critical
    effective_date: datetime | None = None
    encounter_id: str | None = None
    
    @property
    def value(self) -> Any:
        if self.value_numeric is not None:
            return self.value_numeric
        if self.value_boolean is not None:
            return self.value_boolean
        return self.value_string
    
    @property
    def is_abnormal(self) -> bool:
        if self.interpretation:
            return self.interpretation.lower() in ["abnormal", "critical", "high", "low"]
        if self.value_numeric is not None:
            if self.reference_range_low and self.value_numeric < self.reference_range_low:
                return True
            if self.reference_range_high and self.value_numeric > self.reference_range_high:
                return True
        return False


class Procedure(BaseEntity):
    """Clinical procedure entity."""
    patient_id: str
    code: str
    code_system: str = "http://www.ama-assn.org/go/cpt"
    display: str | None = None
    status: str = "completed"
    performed_date: datetime | None = None
    performer_id: str | None = None
    location_id: str | None = None
    encounter_id: str | None = None


class AllergyIntolerance(BaseEntity):
    """Allergy or intolerance entity."""
    patient_id: str
    code: str | None = None
    code_system: str | None = None
    display: str
    category: str | None = None  # food, medication, environment
    criticality: str | None = None  # low, high, unable-to-assess
    clinical_status: str = "active"
    verification_status: str = "confirmed"
    onset_date: datetime | None = None
    reactions: list[str] = Field(default_factory=list)


class Practitioner(BaseEntity):
    """Healthcare practitioner entity."""
    npi: str | None = None
    first_name: str
    last_name: str
    credentials: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    organization_id: str | None = None
    active: bool = True


class Organization(BaseEntity):
    """Healthcare organization entity."""
    name: str
    org_type: str | None = None  # hospital, clinic, payer
    npi: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    parent_id: str | None = None
    active: bool = True
