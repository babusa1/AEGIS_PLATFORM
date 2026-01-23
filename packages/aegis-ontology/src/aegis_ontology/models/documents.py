"""
Documents & Consent Domain Models

FHIR: DocumentReference, Consent, QuestionnaireResponse
"""

from datetime import datetime, date
from typing import Literal
from pydantic import Field
from aegis_ontology.models.base import BaseVertex


class DocumentReference(BaseVertex):
    """Clinical document. FHIR: DocumentReference"""
    
    _label = "DocumentReference"
    _fhir_resource_type = "DocumentReference"
    _omop_table = "note"
    
    status: Literal["current", "superseded", "entered-in-error"] = "current"
    type_code: str = Field(...)
    type_display: str | None = None
    category: Literal["clinical-note", "discharge-summary", "progress-note", "imaging-report", "lab-report", "consent", "other"] = "clinical-note"
    description: str | None = None
    content_type: str | None = None
    content_url: str | None = None
    extracted_text: str | None = None
    created_datetime: datetime | None = None
    patient_id: str = Field(...)
    encounter_id: str | None = None
    author_id: str | None = None


class Consent(BaseVertex):
    """Patient consent. FHIR: Consent"""
    
    _label = "Consent"
    _fhir_resource_type = "Consent"
    _omop_table = None
    
    status: Literal["draft", "active", "inactive", "rejected"] = "active"
    scope: Literal["patient-privacy", "research", "treatment", "data-sharing", "other"] = Field(...)
    category: str = Field(...)
    decision: Literal["deny", "permit"] = "permit"
    period_start: date | None = None
    period_end: date | None = None
    datetime_recorded: datetime = Field(...)
    patient_id: str = Field(...)
    verified: bool = False


class QuestionnaireResponse(BaseVertex):
    """Survey/PRO response. FHIR: QuestionnaireResponse"""
    
    _label = "QuestionnaireResponse"
    _fhir_resource_type = "QuestionnaireResponse"
    _omop_table = "survey_conduct"
    
    questionnaire_id: str = Field(...)
    questionnaire_name: str | None = None
    questionnaire_type: Literal["PHQ-9", "GAD-7", "PROMIS", "EORTC", "KDQOL", "satisfaction", "symptom", "other"] | None = None
    status: Literal["in-progress", "completed", "amended"] = "completed"
    authored_datetime: datetime = Field(...)
    total_score: float | None = None
    severity: Literal["none", "minimal", "mild", "moderate", "severe"] | None = None
    patient_id: str = Field(...)
    encounter_id: str | None = None
    source: Literal["patient", "caregiver", "clinician"] = "patient"


class AdvanceDirective(BaseVertex):
    """Advance directive. FHIR: Consent"""
    
    _label = "AdvanceDirective"
    _fhir_resource_type = "Consent"
    _omop_table = None
    
    type: Literal["living_will", "dnr", "polst", "healthcare_proxy", "organ_donation", "other"] = Field(...)
    status: Literal["active", "inactive"] = "active"
    cpr_preference: Literal["full", "limited", "none"] | None = None
    effective_date: date | None = None
    patient_id: str = Field(...)
    document_id: str | None = None
