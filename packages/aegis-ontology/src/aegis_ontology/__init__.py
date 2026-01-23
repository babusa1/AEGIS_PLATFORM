"""
AEGIS Ontology Package

Healthcare data ontology based on FHIR R4 + OMOP CDM + custom extensions.
This is the "Spine" of the AEGIS platform - the unified data model.

Standards:
- FHIR R4: For clinical data exchange
- OMOP CDM: For analytics and research
- SNOMED-CT: Clinical terminology
- ICD-10: Diagnosis coding
- CPT/HCPCS: Procedure coding
- RxNorm: Medication coding
"""

from aegis_ontology.models.base import BaseVertex, BaseEdge, TenantMixin
from aegis_ontology.models.clinical import (
    Patient,
    Provider,
    Organization,
    Location,
    Encounter,
    Diagnosis,
    Procedure,
    Observation,
    Medication,
    AllergyIntolerance,
)
from aegis_ontology.models.financial import (
    Claim,
    ClaimLine,
    Denial,
    Authorization,
    Coverage,
)
from aegis_ontology.registry import VertexRegistry, EdgeRegistry

__version__ = "0.1.0"

__all__ = [
    # Base
    "BaseVertex",
    "BaseEdge", 
    "TenantMixin",
    # Clinical - Core
    "Patient",
    "Provider",
    "Organization",
    "Location",
    # Clinical - Events
    "Encounter",
    "Diagnosis",
    "Procedure",
    "Observation",
    "Medication",
    "AllergyIntolerance",
    # Financial
    "Claim",
    "ClaimLine",
    "Denial",
    "Authorization",
    "Coverage",
    # Registry
    "VertexRegistry",
    "EdgeRegistry",
]
