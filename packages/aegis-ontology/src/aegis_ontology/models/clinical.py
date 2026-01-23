"""
Clinical Domain Models

FHIR R4 aligned models for clinical entities:
- Patient, Provider, Organization, Location (Core)
- Encounter, Diagnosis, Procedure (Events)
- Observation, Medication, AllergyIntolerance (Clinical Data)

All models map to both FHIR resources and OMOP CDM tables.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from aegis_ontology.models.base import BaseVertex


# ==================== EMBEDDED TYPES ====================

class Address(BaseModel):
    """FHIR-aligned address component."""
    
    use: Literal["home", "work", "temp", "billing"] | None = None
    line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"


class ContactPoint(BaseModel):
    """FHIR-aligned contact point (phone, email)."""
    
    system: Literal["phone", "email", "fax", "url"] = "phone"
    value: str
    use: Literal["home", "work", "mobile"] | None = None


class HumanName(BaseModel):
    """FHIR-aligned human name."""
    
    use: Literal["official", "usual", "nickname", "maiden"] = "official"
    given: str  # First name
    family: str  # Last name
    prefix: str | None = None  # Dr., Mr., etc.
    suffix: str | None = None  # Jr., III, etc.


class CodeableConcept(BaseModel):
    """FHIR CodeableConcept for coded values."""
    
    system: str  # e.g., "http://snomed.info/sct"
    code: str
    display: str | None = None


# ==================== CORE ENTITIES ====================

class Patient(BaseVertex):
    """
    Patient entity - a person receiving healthcare.
    
    FHIR: Patient
    OMOP: person
    """
    
    _label = "Patient"
    _fhir_resource_type = "Patient"
    _omop_table = "person"
    
    # Identifiers
    mrn: str = Field(..., description="Medical Record Number")
    ssn: str | None = Field(default=None, description="SSN (encrypted at rest)")
    
    # Demographics - FHIR aligned
    name: HumanName | None = None
    given_name: str = Field(..., description="First name (denormalized)")
    family_name: str = Field(..., description="Last name (denormalized)")
    birth_date: date = Field(..., description="Date of birth")
    deceased_date: date | None = Field(default=None, description="Date of death")
    gender: Literal["male", "female", "other", "unknown"] = Field(
        ..., description="Administrative gender (FHIR)"
    )
    
    # OMOP specific
    race_concept_id: int | None = Field(default=None, description="OMOP race concept")
    ethnicity_concept_id: int | None = Field(default=None, description="OMOP ethnicity")
    
    # Contact
    phone: str | None = None
    email: str | None = None
    address: Address | None = None
    
    # Relationships (stored as vertex IDs)
    primary_provider_id: str | None = Field(default=None, description="PCP vertex ID")
    managing_organization_id: str | None = Field(default=None, description="Org vertex ID")
    
    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}"
    
    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def is_deceased(self) -> bool:
        return self.deceased_date is not None


class Provider(BaseVertex):
    """
    Healthcare provider (practitioner).
    
    FHIR: Practitioner
    OMOP: provider
    """
    
    _label = "Provider"
    _fhir_resource_type = "Practitioner"
    _omop_table = "provider"
    
    # Identifiers
    npi: str = Field(..., description="National Provider Identifier")
    dea_number: str | None = Field(default=None, description="DEA number")
    
    # Name
    given_name: str
    family_name: str
    credentials: str | None = Field(default=None, description="MD, DO, NP, PA, etc.")
    
    # Specialty - SNOMED coded
    specialty_code: str | None = Field(default=None, description="Specialty SNOMED code")
    specialty_display: str | None = Field(default=None, description="Specialty display name")
    
    # OMOP
    specialty_concept_id: int | None = None
    
    # Contact
    phone: str | None = None
    email: str | None = None
    
    # Organization
    organization_id: str | None = Field(default=None, description="Primary org vertex ID")
    
    @property
    def display_name(self) -> str:
        name = f"{self.given_name} {self.family_name}"
        if self.credentials:
            name += f", {self.credentials}"
        return name


class Organization(BaseVertex):
    """
    Healthcare organization.
    
    FHIR: Organization
    OMOP: care_site (partially)
    """
    
    _label = "Organization"
    _fhir_resource_type = "Organization"
    _omop_table = "care_site"
    
    name: str = Field(..., description="Organization name")
    type: Literal[
        "prov",  # Healthcare provider
        "dept",  # Department
        "pay",   # Payer
        "ins",   # Insurance company
        "govt",  # Government
        "other"
    ] = Field(..., description="Organization type (FHIR)")
    
    # Identifiers
    tax_id: str | None = Field(default=None, description="EIN/Tax ID")
    cms_id: str | None = Field(default=None, description="CMS Certification Number")
    
    # Contact
    phone: str | None = None
    address: Address | None = None
    
    # Hierarchy
    parent_organization_id: str | None = Field(default=None, description="Parent org")
    
    # Status
    active: bool = True


class Location(BaseVertex):
    """
    Physical location (facility, unit, room, bed).
    
    FHIR: Location
    OMOP: care_site, location
    """
    
    _label = "Location"
    _fhir_resource_type = "Location"
    _omop_table = "location"
    
    name: str = Field(..., description="Location name")
    type: Literal[
        "si",    # Site (campus)
        "bu",    # Building
        "wi",    # Wing
        "wa",    # Ward
        "ro",    # Room
        "bd",    # Bed
        "area",  # Area
    ] = Field(..., description="Location type (FHIR)")
    
    # Status (for beds/rooms)
    status: Literal["active", "suspended", "inactive"] = "active"
    operational_status: Literal[
        "available", "occupied", "housekeeping", "contaminated", "blocked"
    ] | None = None
    
    # Hierarchy
    parent_location_id: str | None = None
    organization_id: str | None = None
    
    # Physical
    address: Address | None = None


# ==================== CLINICAL EVENTS ====================

class Encounter(BaseVertex):
    """
    Healthcare encounter (visit, admission).
    
    FHIR: Encounter
    OMOP: visit_occurrence
    """
    
    _label = "Encounter"
    _fhir_resource_type = "Encounter"
    _omop_table = "visit_occurrence"
    
    # Classification (FHIR)
    status: Literal[
        "planned", "arrived", "triaged", "in-progress", 
        "onleave", "finished", "cancelled", "entered-in-error"
    ] = Field(..., description="Encounter status")
    
    class_code: Literal["IMP", "AMB", "EMER", "OBSENC", "SS", "HH", "VR"] = Field(
        ..., description="FHIR class: IMP=inpatient, AMB=ambulatory, EMER=emergency"
    )
    
    type_code: str | None = Field(
        default=None, description="Encounter type (SNOMED)"
    )
    
    # OMOP visit type
    visit_concept_id: int | None = Field(default=None, description="OMOP visit concept")
    
    # Timing
    period_start: datetime = Field(..., description="Encounter start")
    period_end: datetime | None = Field(default=None, description="Encounter end")
    
    # Source/Destination
    admit_source: str | None = Field(default=None, description="Admit source code")
    discharge_disposition: str | None = Field(default=None, description="Discharge disp")
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    attending_provider_id: str | None = None
    admitting_provider_id: str | None = None
    location_id: str | None = None
    
    @property
    def length_of_stay(self) -> int | None:
        if self.period_end:
            return (self.period_end - self.period_start).days
        return None
    
    @property
    def is_inpatient(self) -> bool:
        return self.class_code == "IMP"


class Diagnosis(BaseVertex):
    """
    Diagnosis/Condition.
    
    FHIR: Condition
    OMOP: condition_occurrence
    """
    
    _label = "Diagnosis"
    _fhir_resource_type = "Condition"
    _omop_table = "condition_occurrence"
    
    # Coding - ICD-10-CM
    code: str = Field(..., description="ICD-10-CM code")
    code_system: str = Field(
        default="http://hl7.org/fhir/sid/icd-10-cm",
        description="Code system URI"
    )
    display: str = Field(..., description="Diagnosis description")
    
    # OMOP
    condition_concept_id: int | None = None
    condition_type_concept_id: int | None = None
    
    # Classification
    category: Literal["encounter-diagnosis", "problem-list-item"] = "encounter-diagnosis"
    use: Literal["AD", "DD", "CC", "CM", "pre-op", "post-op", "billing"] | None = Field(
        default=None, description="AD=admitting, DD=discharge, CC=chief complaint"
    )
    rank: int = Field(default=1, description="Diagnosis sequence (1=principal)")
    
    # Clinical
    clinical_status: Literal["active", "recurrence", "relapse", "inactive", "remission", "resolved"] | None = None
    verification_status: Literal["unconfirmed", "provisional", "differential", "confirmed", "refuted"] | None = None
    
    # Timing
    onset_date: date | None = None
    abatement_date: date | None = None
    recorded_date: datetime | None = None
    
    # POA for inpatient
    present_on_admission: Literal["Y", "N", "U", "W", "1"] | None = Field(
        default=None, description="Present on admission indicator"
    )
    
    # Relationships
    encounter_id: str = Field(..., description="Encounter vertex ID")
    asserter_id: str | None = None  # Provider who made diagnosis
    
    @property
    def is_principal(self) -> bool:
        return self.rank == 1 or self.use == "DD"


class Procedure(BaseVertex):
    """
    Clinical procedure.
    
    FHIR: Procedure
    OMOP: procedure_occurrence
    """
    
    _label = "Procedure"
    _fhir_resource_type = "Procedure"
    _omop_table = "procedure_occurrence"
    
    # Coding - CPT/HCPCS/ICD-10-PCS
    code: str = Field(..., description="Procedure code")
    code_system: Literal[
        "http://www.ama-assn.org/go/cpt",
        "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets",
        "http://hl7.org/fhir/sid/icd-10-pcs"
    ] = Field(..., description="Code system")
    display: str = Field(..., description="Procedure description")
    
    # OMOP
    procedure_concept_id: int | None = None
    procedure_type_concept_id: int | None = None
    
    # Timing
    performed_datetime: datetime = Field(..., description="When performed")
    
    # Status
    status: Literal[
        "preparation", "in-progress", "not-done", 
        "on-hold", "stopped", "completed", "entered-in-error"
    ] = "completed"
    
    # Relationships
    encounter_id: str = Field(..., description="Encounter vertex ID")
    performer_id: str | None = Field(default=None, description="Performing provider")
    location_id: str | None = None
    
    # Modifiers
    modifier_codes: list[str] | None = None


class Observation(BaseVertex):
    """
    Clinical observation (vitals, labs, assessments).
    
    FHIR: Observation
    OMOP: measurement, observation
    """
    
    _label = "Observation"
    _fhir_resource_type = "Observation"
    _omop_table = "measurement"
    
    # Coding - LOINC
    code: str = Field(..., description="LOINC code")
    code_system: str = Field(
        default="http://loinc.org",
        description="Code system"
    )
    display: str | None = None
    
    # Category
    category: Literal[
        "vital-signs", "laboratory", "imaging", 
        "procedure", "survey", "exam", "social-history"
    ] = Field(..., description="Observation category")
    
    # Value
    value_quantity: float | None = None
    value_string: str | None = None
    value_codeable_concept: CodeableConcept | None = None
    unit: str | None = None
    
    # OMOP
    measurement_concept_id: int | None = None
    
    # Reference range
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    reference_range_text: str | None = None
    
    # Interpretation
    interpretation: Literal[
        "N", "A", "AA", "HH", "LL", "H", "L", "HU", "LU"
    ] | None = Field(default=None, description="HL7 interpretation codes")
    
    # Timing
    effective_datetime: datetime = Field(..., description="When observed")
    issued: datetime | None = None
    
    # Status
    status: Literal[
        "registered", "preliminary", "final", 
        "amended", "corrected", "cancelled", "entered-in-error"
    ] = "final"
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    performer_id: str | None = None
    
    @property
    def is_abnormal(self) -> bool:
        return self.interpretation in ("A", "AA", "HH", "LL", "H", "L", "HU", "LU")
    
    @property
    def is_critical(self) -> bool:
        return self.interpretation in ("AA", "HH", "LL")


class Medication(BaseVertex):
    """
    Medication request/administration.
    
    FHIR: MedicationRequest, MedicationAdministration
    OMOP: drug_exposure
    """
    
    _label = "Medication"
    _fhir_resource_type = "MedicationRequest"
    _omop_table = "drug_exposure"
    
    # Coding - RxNorm
    code: str = Field(..., description="RxNorm code")
    code_system: str = Field(
        default="http://www.nlm.nih.gov/research/umls/rxnorm",
        description="Code system"
    )
    display: str = Field(..., description="Medication name")
    
    # OMOP
    drug_concept_id: int | None = None
    drug_type_concept_id: int | None = None
    
    # Dosage
    dose_value: float | None = None
    dose_unit: str | None = None
    route: str | None = Field(default=None, description="Route: oral, IV, IM, etc.")
    frequency: str | None = Field(default=None, description="Frequency: QD, BID, etc.")
    
    # Timing
    effective_start: datetime | None = None
    effective_end: datetime | None = None
    
    # Status
    status: Literal[
        "active", "on-hold", "cancelled", "completed",
        "entered-in-error", "stopped", "draft"
    ] = "active"
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    prescriber_id: str | None = None
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"


class AllergyIntolerance(BaseVertex):
    """
    Allergy or intolerance.
    
    FHIR: AllergyIntolerance
    OMOP: (no direct mapping)
    """
    
    _label = "AllergyIntolerance"
    _fhir_resource_type = "AllergyIntolerance"
    _omop_table = None
    
    # Substance
    code: str | None = Field(default=None, description="Allergen code (RxNorm, etc.)")
    display: str = Field(..., description="Allergen name")
    
    # Classification
    type: Literal["allergy", "intolerance"] = "allergy"
    category: Literal["food", "medication", "environment", "biologic"] | None = None
    criticality: Literal["low", "high", "unable-to-assess"] | None = None
    
    # Reaction
    reaction_manifestation: str | None = None
    reaction_severity: Literal["mild", "moderate", "severe"] | None = None
    
    # Status
    clinical_status: Literal["active", "inactive", "resolved"] = "active"
    verification_status: Literal["unconfirmed", "confirmed", "refuted", "entered-in-error"] = "confirmed"
    
    # Timing
    onset_datetime: datetime | None = None
    recorded_date: datetime | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    recorder_id: str | None = None
