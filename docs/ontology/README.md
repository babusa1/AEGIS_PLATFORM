# AEGIS Healthcare Ontology

## Overview

The AEGIS ontology defines the data model for healthcare entities and their relationships. It's based on industry standards (FHIR R4, OMOP CDM) with custom extensions for financial and quality domains.

## Standards Used

| Domain | Standard | Purpose |
|--------|----------|---------|
| Clinical | HL7 FHIR R4 | Primary clinical data model |
| Analytics | OMOP CDM | Research-ready data |
| Terminology | SNOMED-CT | Clinical concepts |
| Diagnosis | ICD-10-CM | Diagnosis coding |
| Procedures | CPT/HCPCS | Procedure coding |
| Medications | RxNorm | Drug terminology |
| Financial | AEGIS Custom | Claims, Denials, Appeals |

## Entity Domains

### Clinical Domain

| Entity | FHIR Resource | Description |
|--------|---------------|-------------|
| Patient | Patient | Person receiving care |
| Encounter | Encounter | Healthcare visit/admission |
| Condition | Condition | Diagnosis (ICD-10 coded) |
| Procedure | Procedure | Clinical procedure (CPT coded) |
| Observation | Observation | Labs, vitals, assessments |
| Medication | MedicationRequest | Prescriptions |
| AllergyIntolerance | AllergyIntolerance | Patient allergies |

### Provider Domain

| Entity | FHIR Resource | Description |
|--------|---------------|-------------|
| Provider | Practitioner | Physician, nurse, etc. |
| Organization | Organization | Hospital, clinic, payer |
| Location | Location | Facility, unit, room, bed |

### Financial Domain

| Entity | FHIR Resource | Description |
|--------|---------------|-------------|
| Claim | Claim | Professional/institutional claim |
| ClaimLine | ClaimItem | Individual service line |
| Denial | Custom | Claim denial with CARC/RARC |
| Appeal | Custom | Appeal submission |
| Payment | PaymentReconciliation | Remittance |
| Coverage | Coverage | Insurance coverage |
| Payer | Organization | Insurance company |
| Authorization | Custom | Prior authorization |

### Quality Domain

| Entity | FHIR Resource | Description |
|--------|---------------|-------------|
| QualityMeasure | Measure | HEDIS/CMS measure definition |
| CareGap | Custom | Identified quality gap |
| Intervention | Custom | Gap closure action |

## Graph Schema

### Vertex Labels

```
Patient
Encounter
Condition
Procedure
Observation
Medication
AllergyIntolerance
Provider
Organization
Location
Claim
ClaimLine
Denial
Appeal
Payment
Coverage
Payer
Authorization
QualityMeasure
CareGap
Intervention
Tenant
User
AuditLog
```

### Edge Labels (Relationships)

```
Patient Relationships:
  Patient --[HAS_ENCOUNTER]--> Encounter
  Patient --[HAS_CONDITION]--> Condition
  Patient --[HAS_MEDICATION]--> Medication
  Patient --[HAS_ALLERGY]--> AllergyIntolerance
  Patient --[HAS_COVERAGE]--> Coverage
  Patient --[HAS_CARE_GAP]--> CareGap

Encounter Relationships:
  Encounter --[HAS_DIAGNOSIS]--> Condition
  Encounter --[HAS_PROCEDURE]--> Procedure
  Encounter --[HAS_OBSERVATION]--> Observation
  Encounter --[ATTENDED_BY]--> Provider
  Encounter --[AT_LOCATION]--> Location
  Encounter --[BILLED_AS]--> Claim

Claim Relationships:
  Claim --[HAS_LINE]--> ClaimLine
  Claim --[SUBMITTED_TO]--> Payer
  Claim --[DENIED_WITH]--> Denial
  Claim --[PAID_BY]--> Payment

Denial Relationships:
  Denial --[APPEALED_BY]--> Appeal
  Denial --[ISSUED_BY]--> Payer

Quality Relationships:
  CareGap --[FOR_MEASURE]--> QualityMeasure
  CareGap --[CLOSED_BY]--> Intervention
  Intervention --[PERFORMED_BY]--> Provider

Provider Relationships:
  Provider --[WORKS_AT]--> Organization
  Provider --[HAS_ROLE]--> PractitionerRole

Organization Relationships:
  Organization --[PARENT_OF]--> Organization
  Organization --[HAS_LOCATION]--> Location
```

## Vertex Properties

### Patient

```yaml
Patient:
  # Identifiers
  id: string (UUID)
  mrn: string (Medical Record Number)
  fhir_id: string (optional)
  ssn_hash: string (optional, for matching)
  
  # Demographics
  given_name: string
  family_name: string
  birth_date: date
  gender: enum [male, female, other, unknown]
  deceased: boolean
  deceased_date: date (optional)
  
  # Contact
  phone_number: string (optional)
  email: string (optional)
  address_line: string (optional)
  city: string (optional)
  state: string (optional)
  postal_code: string (optional)
  
  # Platform
  tenant_id: string (required)
  source_system: string
  created_at: datetime
  updated_at: datetime
```

### Claim

```yaml
Claim:
  # Identifiers
  id: string (UUID)
  claim_number: string
  
  # Classification
  type: enum [professional, institutional, dental, pharmacy]
  status: enum [draft, submitted, pending, paid, denied, appealed]
  
  # Dates
  service_date_start: date
  service_date_end: date (optional)
  submission_date: date (optional)
  
  # Amounts
  billed_amount: decimal
  allowed_amount: decimal (optional)
  paid_amount: decimal (optional)
  patient_responsibility: decimal (optional)
  
  # Diagnosis
  primary_diagnosis: string (ICD-10)
  secondary_diagnoses: list[string]
  
  # Platform
  tenant_id: string
  source_system: string
  created_at: datetime
  updated_at: datetime
```

### Denial

```yaml
Denial:
  # Identifiers
  id: string (UUID)
  
  # Reason
  reason_code: string (CARC/RARC)
  category: enum [
    medical_necessity,
    authorization,
    coding,
    eligibility,
    duplicate,
    timely_filing,
    bundling,
    other
  ]
  description: string
  
  # Amounts
  denied_amount: decimal
  
  # Dates
  denial_date: date
  appeal_deadline: date (optional)
  
  # Platform
  tenant_id: string
  created_at: datetime
```

### CareGap

```yaml
CareGap:
  # Identifiers
  id: string (UUID)
  
  # Classification
  measure_id: string (HEDIS/CMS code)
  gap_type: string
  priority: enum [high, medium, low]
  status: enum [open, pending, closed]
  
  # Dates
  identified_date: date
  due_date: date (optional)
  closed_date: date (optional)
  
  # Evidence
  evidence_summary: string (optional)
  
  # Platform
  tenant_id: string
  created_at: datetime
  updated_at: datetime
```

## Query Examples

### Patient 360 View

```gremlin
g.V().has('Patient', 'id', patientId)
     .has('tenant_id', tenantId)
     .project('patient', 'encounters', 'conditions', 'claims', 'care_gaps')
     .by(valueMap())
     .by(out('HAS_ENCOUNTER').order().by('admit_date', desc).limit(50).valueMap().fold())
     .by(out('HAS_CONDITION').has('status', 'active').valueMap().fold())
     .by(out('HAS_ENCOUNTER').out('BILLED_AS').valueMap().fold())
     .by(out('HAS_CARE_GAP').has('status', 'open').valueMap().fold())
```

### Denied Claims for Patient

```gremlin
g.V().has('Patient', 'id', patientId)
     .out('HAS_ENCOUNTER')
     .out('BILLED_AS')
     .has('status', 'denied')
     .out('DENIED_WITH')
     .valueMap()
```

### High-Priority Care Gaps

```gremlin
g.V().has('CareGap', 'tenant_id', tenantId)
     .has('status', 'open')
     .has('priority', 'high')
     .order().by('due_date', asc)
     .limit(100)
     .valueMap()
```

## Data Lineage

Every entity tracks its source:

```yaml
source_system: "epic"           # Origin system
source_id: "E12345"             # ID in source system
created_at: "2024-01-15T..."    # When ingested
updated_at: "2024-01-16T..."    # Last update
tenant_id: "hospital_a"         # Owning tenant
```

## References

- [HL7 FHIR R4](https://hl7.org/fhir/R4/)
- [OMOP CDM](https://ohdsi.github.io/CommonDataModel/)
- [SNOMED-CT](https://www.snomed.org/)
- [ICD-10-CM](https://www.cdc.gov/nchs/icd/icd10cm.htm)
