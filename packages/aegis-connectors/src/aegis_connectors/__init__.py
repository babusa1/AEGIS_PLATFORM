"""
AEGIS Data Connectors

Production connectors for 19+ healthcare data sources:
- FHIR R4 (EHRs, modern APIs)
- HL7v2 (ADT, labs, legacy)
- X12 EDI (claims, eligibility)
- Devices (wearables, IoMT)
- Genomics (VCF, variants)
- Documents (CDA, PDF)
"""

from aegis_connectors.base import BaseConnector, ConnectorResult

__version__ = "0.1.0"

__all__ = ["BaseConnector", "ConnectorResult"]
