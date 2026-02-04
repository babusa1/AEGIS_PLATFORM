"""
AEGIS Healthcare Integrations

Industry-standard healthcare integrations:
- Epic FHIR R4
- Cerner FHIR R4
- HL7v2 (ADT, ORM, ORU, etc.)
- X12 EDI (837, 835)
- NCPDP (Pharmacy)
"""

from aegis.integrations.fhir import FHIRClient, FHIRResource, EpicFHIRClient
from aegis.integrations.hl7v2 import HL7v2Parser, HL7v2Message, HL7v2Segment
from aegis.integrations.terminology import (
    TerminologyService,
    ICD10Lookup,
    CPTLookup,
    SNOMEDLookup,
    RxNormLookup,
)

__all__ = [
    "FHIRClient",
    "FHIRResource",
    "EpicFHIRClient",
    "HL7v2Parser",
    "HL7v2Message",
    "HL7v2Segment",
    "TerminologyService",
    "ICD10Lookup",
    "CPTLookup",
    "SNOMEDLookup",
    "RxNormLookup",
]
