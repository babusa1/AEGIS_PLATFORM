# ADR-002: Healthcare Ontology Standards

## Status
Accepted

## Context
AEGIS needs a standardized data model (ontology) for healthcare data. We must decide which industry standards to adopt and how to extend them for our specific use cases.

## Decision
**Hybrid approach**: Start with HL7 FHIR R4 as the primary standard, augmented with OMOP CDM for analytics and custom extensions for financial/RCM data.

### Standards Adopted

| Domain | Standard | Purpose |
|--------|----------|---------|
| Clinical | HL7 FHIR R4 | Patient, Encounter, Condition, Procedure, Observation |
| Analytics | OMOP CDM | Research-ready data transformations |
| Terminology | SNOMED-CT | Clinical concepts |
| Diagnosis | ICD-10-CM | Diagnosis coding |
| Procedures | CPT/HCPCS | Procedure coding |
| Medications | RxNorm | Drug terminology |
| Financial | Custom (AEGIS) | Claims, Denials, Appeals (not well-covered by FHIR) |

### Why FHIR R4?
1. **Industry standard**: Mandated by ONC for US healthcare
2. **Interoperability**: Direct mapping from EHR systems
3. **Well-documented**: Extensive specifications and examples
4. **RESTful**: Natural fit for API design

### Custom Extensions (Financial Domain)
FHIR's Claim resource is limited. We extend with:
- `Denial` - Claim denial with CARC/RARC codes
- `Appeal` - Appeal submissions and outcomes
- `CareGap` - Quality measure gaps
- `QualityMeasure` - HEDIS/CMS measure definitions

## Graph Schema Mapping

```
FHIR Resource     →  Graph Vertex
---------------------------------
Patient           →  Patient
Encounter         →  Encounter
Condition         →  Condition
Procedure         →  Procedure
Observation       →  Observation
MedicationRequest →  Medication
Practitioner      →  Provider
Organization      →  Organization
Claim             →  Claim
Coverage          →  Coverage
```

## Consequences
- All clinical entities follow FHIR R4 structure
- Financial entities use custom schema (documented)
- FHIR-to-Graph mapping layer required for ingestion
- Can export data as valid FHIR bundles for interoperability

## References
- [HL7 FHIR R4](https://hl7.org/fhir/R4/)
- [OMOP CDM](https://ohdsi.github.io/CommonDataModel/)
- [US Core FHIR Profiles](https://www.hl7.org/fhir/us/core/)
