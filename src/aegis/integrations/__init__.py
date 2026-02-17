"""
VeritOS Healthcare Integrations

Industry-standard healthcare integrations:
- Epic FHIR R4
- Cerner FHIR R4
- HL7v2 (ADT, ORM, ORU, etc.)
- X12 EDI (837, 835)
- NCPDP (Pharmacy)
- Terminology Services (ICD-10, CPT, SNOMED, RxNorm, LOINC)
- FHIR Profile Validation
"""

from aegis.integrations.fhir import FHIRClient, FHIRResource, EpicFHIRClient
from aegis.integrations.hl7v2 import HL7v2Parser, HL7v2Message, HL7v2Segment
from aegis.integrations.terminology import (
    TerminologyService,
    CachedTerminologyService,
    ICD10Lookup,
    CPTLookup,
    SNOMEDLookup,
    RxNormLookup,
    LOINCLookup,
    CodeInfo,
    CodeSearchResult,
)
from aegis.integrations.fhir_validator import (
    FHIRProfileValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationCategory,
    validate_resource,
    validate_bundle,
    get_validator,
    US_CORE_PROFILES,
)

__all__ = [
    # FHIR
    "FHIRClient",
    "FHIRResource",
    "EpicFHIRClient",
    # HL7v2
    "HL7v2Parser",
    "HL7v2Message",
    "HL7v2Segment",
    # Terminology
    "TerminologyService",
    "CachedTerminologyService",
    "ICD10Lookup",
    "CPTLookup",
    "SNOMEDLookup",
    "RxNormLookup",
    "LOINCLookup",
    "CodeInfo",
    "CodeSearchResult",
    # FHIR Validation
    "FHIRProfileValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "ValidationCategory",
    "validate_resource",
    "validate_bundle",
    "get_validator",
    "US_CORE_PROFILES",
]
