"""
Imaging Domain Models

Models for radiology/imaging data:
- ImagingStudy (DICOM study)
- ImagingReport (radiology report)

FHIR: ImagingStudy, DiagnosticReport
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class ImagingStudy(BaseVertex):
    """
    Imaging study (DICOM).
    
    FHIR: ImagingStudy
    """
    
    _label = "ImagingStudy"
    _fhir_resource_type = "ImagingStudy"
    _omop_table = None
    
    # Identifiers
    study_instance_uid: str = Field(..., description="DICOM Study Instance UID")
    accession_number: str | None = None
    
    # Modality
    modality: str = Field(..., description="Primary modality (CT, MR, US, etc.)")
    modality_list: list[str] | None = None
    
    # Study info
    description: str | None = None
    body_site: str | None = None
    laterality: str | None = None
    
    # Status
    status: Literal["registered", "available", "cancelled", "entered-in-error"] = "available"
    
    # Counts
    number_of_series: int | None = None
    number_of_instances: int | None = None
    
    # Timing
    started_datetime: datetime = Field(..., description="Study start time")
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    ordering_provider_id: str | None = None
    report_id: str | None = None


class ImagingReport(BaseVertex):
    """
    Radiology report.
    
    FHIR: DiagnosticReport
    """
    
    _label = "ImagingReport"
    _fhir_resource_type = "DiagnosticReport"
    _omop_table = None
    
    # Status
    status: Literal["preliminary", "final", "amended", "cancelled"] = "final"
    
    # Content
    conclusion: str | None = None
    narrative: str | None = None
    findings: list[str] | None = None
    
    # Critical
    is_critical: bool = False
    
    # Timing
    effective_datetime: datetime | None = None
    issued_datetime: datetime | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    study_id: str | None = None
    performer_id: str | None = None
    
    # AI findings
    ai_findings: list[str] | None = None
