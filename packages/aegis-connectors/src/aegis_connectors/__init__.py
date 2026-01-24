"""
AEGIS Data Connectors

Production connectors for 31 healthcare data sources:

Tier 1 - Clinical Core:
- FHIR R4 (EHRs, modern APIs)
- HL7v2 (ADT, labs, legacy)
- CDA/CCDA (clinical documents)

Tier 2 - Financial:
- X12 837/835 (claims)
- X12 270/271 (eligibility)
- X12 276/277 (claim status)
- X12 278 (prior auth)

Tier 3 - Devices:
- Apple HealthKit
- Google Fit
- Fitbit
- Garmin
- Withings

Tier 4 - Specialized:
- Genomics (VCF, GA4GH)
- Imaging (DICOM, DICOMweb)
- SDOH (PRAPARE, social determinants)
- PRO Forms (patient-reported outcomes)
- Messaging (patient communications)

Tier 5 - Operations & Knowledge:
- Scheduling (appointments)
- Workflow (tasks, care gaps)
- Analytics (HEDIS, risk scores)
- Guidelines (clinical rules)
- Drug Labels (FDA, RxNorm)
- Consent (FHIR Consent)
"""

from aegis_connectors.base import BaseConnector, ConnectorResult

__version__ = "0.2.0"

__all__ = ["BaseConnector", "ConnectorResult"]
