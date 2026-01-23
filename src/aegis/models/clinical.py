"""
Clinical Domain Models

Pydantic models for Encounter, Diagnosis, Procedure, Observation, Medication.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from aegis.models.core import BaseEntity


class Encounter(BaseEntity):
    """
    Encounter entity.
    
    Represents a healthcare encounter (admission, visit, etc.).
    Maps to FHIR Encounter resource.
    """
    
    # Classification
    type: Literal["inpatient", "outpatient", "emergency", "observation", "ambulatory"] = Field(
        ..., description="Encounter type"
    )
    encounter_class: str = Field(
        default="IMP", 
        description="FHIR class code: IMP, AMB, EMER, etc."
    )
    status: Literal["planned", "in-progress", "finished", "cancelled", "entered-in-error"] = Field(
        ..., description="Encounter status"
    )
    
    # Timing
    admit_date: datetime = Field(..., description="Admission/start datetime")
    discharge_date: datetime | None = Field(default=None, description="Discharge/end datetime")
    
    # Source/Destination
    admit_source: str | None = Field(
        default=None, 
        description="Admit source: emergency, transfer, physician_referral"
    )
    discharge_disposition: str | None = Field(
        default=None,
        description="Discharge disposition: home, snf, rehab, expired"
    )
    
    # Relationships (vertex IDs)
    patient_id: str = Field(..., description="Patient vertex ID")
    attending_provider_id: str | None = Field(default=None, description="Attending provider")
    location_id: str | None = Field(default=None, description="Current location")
    
    @property
    def length_of_stay(self) -> int | None:
        """Calculate length of stay in days."""
        if self.discharge_date:
            delta = self.discharge_date - self.admit_date
            return delta.days
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if encounter is currently active."""
        return self.status == "in-progress"


class Diagnosis(BaseEntity):
    """
    Diagnosis entity.
    
    Represents a clinical diagnosis/condition (ICD-10 coded).
    Maps to FHIR Condition resource.
    """
    
    # Coding
    icd10_code: str = Field(..., description="ICD-10-CM code")
    description: str = Field(..., description="Diagnosis description")
    
    # Classification
    type: Literal["admitting", "principal", "secondary", "comorbidity", "complication"] = Field(
        default="secondary", description="Diagnosis type"
    )
    rank: int = Field(default=1, description="Diagnosis rank (1 = primary)")
    
    # Clinical
    present_on_admission: Literal["Y", "N", "U", "W"] | None = Field(
        default=None, description="POA indicator"
    )
    onset_date: date | None = Field(default=None, description="Condition onset date")
    
    # Relationships
    encounter_id: str = Field(..., description="Associated encounter")
    
    @property
    def is_primary(self) -> bool:
        """Check if this is the primary diagnosis."""
        return self.rank == 1 or self.type == "principal"


class Procedure(BaseEntity):
    """
    Procedure entity.
    
    Represents a clinical procedure (CPT/HCPCS coded).
    Maps to FHIR Procedure resource.
    """
    
    # Coding
    cpt_code: str | None = Field(default=None, description="CPT code")
    hcpcs_code: str | None = Field(default=None, description="HCPCS code")
    description: str = Field(..., description="Procedure description")
    
    # Timing
    procedure_date: datetime = Field(..., description="Procedure datetime")
    
    # Status
    status: Literal["preparation", "in-progress", "completed", "cancelled"] = Field(
        default="completed", description="Procedure status"
    )
    
    # Relationships
    encounter_id: str = Field(..., description="Associated encounter")
    performed_by_id: str | None = Field(default=None, description="Performing provider")
    
    @property
    def procedure_code(self) -> str | None:
        """Get the primary procedure code."""
        return self.cpt_code or self.hcpcs_code


class Observation(BaseEntity):
    """
    Observation entity.
    
    Represents a clinical observation (vital signs, labs, assessments).
    Maps to FHIR Observation resource.
    """
    
    # Coding
    loinc_code: str | None = Field(default=None, description="LOINC code")
    type: Literal["vital-signs", "laboratory", "assessment", "imaging", "social-history"] = Field(
        ..., description="Observation category"
    )
    
    # Value
    value: str = Field(..., description="Observation value (as string)")
    value_numeric: float | None = Field(default=None, description="Numeric value if applicable")
    unit: str | None = Field(default=None, description="Unit of measure")
    
    # Interpretation
    reference_range: str | None = Field(default=None, description="Reference range")
    interpretation: Literal["normal", "abnormal", "critical", "high", "low"] | None = Field(
        default=None, description="Interpretation"
    )
    
    # Timing
    observation_date: datetime = Field(..., description="Observation datetime")
    
    # Relationships
    encounter_id: str | None = Field(default=None, description="Associated encounter")
    patient_id: str = Field(..., description="Patient ID")
    
    @property
    def is_critical(self) -> bool:
        """Check if observation has critical interpretation."""
        return self.interpretation == "critical"
    
    @property
    def is_abnormal(self) -> bool:
        """Check if observation is abnormal."""
        return self.interpretation in ("abnormal", "critical", "high", "low")


class Medication(BaseEntity):
    """
    Medication entity.
    
    Represents a medication order or administration.
    Maps to FHIR MedicationRequest/MedicationAdministration resources.
    """
    
    # Coding
    ndc_code: str | None = Field(default=None, description="NDC code")
    rxnorm_code: str | None = Field(default=None, description="RxNorm code")
    name: str = Field(..., description="Medication name")
    
    # Dosing
    dosage: str | None = Field(default=None, description="Dosage (e.g., '500mg')")
    route: str | None = Field(default=None, description="Route: oral, IV, IM, etc.")
    frequency: str | None = Field(default=None, description="Frequency (e.g., 'BID')")
    
    # Status
    status: Literal["active", "completed", "stopped", "on-hold", "entered-in-error"] = Field(
        default="active", description="Medication status"
    )
    
    # Timing
    start_date: datetime | None = Field(default=None, description="Start datetime")
    end_date: datetime | None = Field(default=None, description="End datetime")
    
    # Relationships
    patient_id: str = Field(..., description="Patient ID")
    prescriber_id: str | None = Field(default=None, description="Prescribing provider")
    encounter_id: str | None = Field(default=None, description="Associated encounter")
    
    @property
    def is_active(self) -> bool:
        """Check if medication is currently active."""
        return self.status == "active"


class AllergyIntolerance(BaseEntity):
    """
    Allergy/Intolerance entity.
    
    Represents patient allergies and intolerances.
    Maps to FHIR AllergyIntolerance resource.
    """
    
    # Allergen
    substance: str = Field(..., description="Allergen substance")
    substance_code: str | None = Field(default=None, description="Substance code (RxNorm, etc.)")
    
    # Reaction
    reaction: str | None = Field(default=None, description="Reaction description")
    severity: Literal["mild", "moderate", "severe"] | None = Field(
        default=None, description="Reaction severity"
    )
    
    # Classification
    type: Literal["allergy", "intolerance"] = Field(
        default="allergy", description="Allergy or intolerance"
    )
    category: Literal["food", "medication", "environment", "biologic"] | None = Field(
        default=None, description="Allergen category"
    )
    
    # Status
    status: Literal["active", "inactive", "resolved"] = Field(
        default="active", description="Clinical status"
    )
    
    # Relationships
    patient_id: str = Field(..., description="Patient ID")
