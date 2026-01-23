# AEGIS Ontology

Healthcare data ontology for the AEGIS Platform - the "Spine" that unifies all data sources.

## Overview

This package provides Pydantic models aligned with:
- **FHIR R4**: HL7 FHIR standard for healthcare data exchange
- **OMOP CDM**: Observational Medical Outcomes Partnership Common Data Model
- **Custom Extensions**: AEGIS-specific fields for multi-tenancy and AI

## Installation

```bash
pip install aegis-ontology
```

## Quick Start

```python
from aegis_ontology import Patient, Encounter, Diagnosis, Claim, Denial

# Create a patient
patient = Patient(
    tenant_id="hospital-a",
    mrn="12345",
    given_name="John",
    family_name="Doe",
    birth_date="1980-05-15",
    gender="male"
)

# Create an encounter
encounter = Encounter(
    tenant_id="hospital-a",
    patient_id=patient.id,
    status="in-progress",
    class_code="IMP",  # Inpatient
    period_start=datetime.now()
)

# Create a diagnosis
diagnosis = Diagnosis(
    tenant_id="hospital-a",
    encounter_id=encounter.id,
    code="I10",  # Essential hypertension
    display="Essential (primary) hypertension",
    rank=1
)

# Convert to graph properties
graph_props = patient.to_graph_properties()
```

## Data Model

### Core Entities (Clinical)

| Model | FHIR Resource | OMOP Table | Description |
|-------|---------------|------------|-------------|
| `Patient` | Patient | person | Person receiving care |
| `Provider` | Practitioner | provider | Healthcare provider |
| `Organization` | Organization | care_site | Healthcare organization |
| `Location` | Location | location | Physical location |

### Clinical Events

| Model | FHIR Resource | OMOP Table | Description |
|-------|---------------|------------|-------------|
| `Encounter` | Encounter | visit_occurrence | Healthcare visit |
| `Diagnosis` | Condition | condition_occurrence | Diagnosis/condition |
| `Procedure` | Procedure | procedure_occurrence | Clinical procedure |
| `Observation` | Observation | measurement | Labs, vitals, assessments |
| `Medication` | MedicationRequest | drug_exposure | Medication orders |
| `AllergyIntolerance` | AllergyIntolerance | - | Allergies |

### Financial (RCM)

| Model | Description |
|-------|-------------|
| `Coverage` | Insurance coverage |
| `Claim` | Healthcare claim |
| `ClaimLine` | Claim line item |
| `Denial` | Claim denial with reason codes |
| `Authorization` | Prior authorization |

## Edge Types (Relationships)

```
Patient --HAS_ENCOUNTER--> Encounter
Encounter --HAS_DIAGNOSIS--> Diagnosis
Encounter --HAS_PROCEDURE--> Procedure
Patient --HAS_OBSERVATION--> Observation
Patient --HAS_MEDICATION--> Medication
Encounter --TREATED_BY--> Provider
Provider --BELONGS_TO--> Organization
Patient --HAS_COVERAGE--> Coverage
Encounter --HAS_CLAIM--> Claim
Claim --HAS_DENIAL--> Denial
```

## Multi-Tenancy

All models include `tenant_id` for multi-tenant isolation:

```python
patient = Patient(
    tenant_id="hospital-a",  # Tenant isolation
    mrn="12345",
    ...
)
```

## FHIR/OMOP Mapping

Get the FHIR resource type or OMOP table for any model:

```python
from aegis_ontology.registry import get_fhir_mapping, get_omop_mapping

fhir_type = get_fhir_mapping("Patient")  # "Patient"
omop_table = get_omop_mapping("Encounter")  # "visit_occurrence"
```

## Schema Validation

Validate properties against the schema:

```python
from aegis_ontology.registry import validate_vertex

patient = validate_vertex("Patient", {
    "mrn": "12345",
    "given_name": "John",
    "family_name": "Doe",
    "birth_date": "1980-05-15",
    "gender": "male"
})
```

## JSON Schema

Get JSON schema for API documentation:

```python
from aegis_ontology.registry import get_vertex_schema

schema = get_vertex_schema("Patient")
print(schema)  # JSON Schema dict
```

## License

MIT
