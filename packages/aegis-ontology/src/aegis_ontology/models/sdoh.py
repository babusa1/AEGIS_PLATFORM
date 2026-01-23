"""
Social Determinants of Health (SDOH) Domain Models

FHIR: Observation (social-history), Condition
"""

from datetime import date, datetime
from typing import Literal
from pydantic import Field
from aegis_ontology.models.base import BaseVertex


class SocialHistory(BaseVertex):
    """Social history observation. FHIR: Observation"""
    
    _label = "SocialHistory"
    _fhir_resource_type = "Observation"
    _omop_table = "observation"
    
    type: Literal["tobacco_use", "alcohol_use", "drug_use", "occupation", "education", "other"] = Field(...)
    code: str | None = None
    value: str = Field(...)
    smoking_status: Literal["current_smoker", "former_smoker", "never_smoker", "unknown"] | None = None
    packs_per_day: float | None = None
    years_smoked: int | None = None
    drinks_per_week: float | None = None
    effective_datetime: datetime | None = None
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None


class SDOHAssessment(BaseVertex):
    """SDOH screening assessment. FHIR: Observation"""
    
    _label = "SDOHAssessment"
    _fhir_resource_type = "Observation"
    _omop_table = None
    
    assessment_type: Literal["PRAPARE", "AHC-HRSN", "food_insecurity", "housing", "transportation", "other"] = Field(...)
    status: Literal["final", "preliminary", "entered-in-error"] = "final"
    positive_screen: bool = Field(...)
    risk_level: Literal["low", "moderate", "high"] | None = None
    score: float | None = None
    food_insecurity: bool | None = None
    housing_instability: bool | None = None
    transportation_needs: bool | None = None
    effective_datetime: datetime = Field(...)
    patient_id: str = Field(...)
    encounter_id: str | None = None


class SDOHCondition(BaseVertex):
    """SDOH-related condition. FHIR: Condition"""
    
    _label = "SDOHCondition"
    _fhir_resource_type = "Condition"
    _omop_table = None
    
    category: Literal["food_insecurity", "housing_instability", "homelessness", "transportation_insecurity", "financial_strain", "social_isolation", "other"] = Field(...)
    code: str = Field(...)
    display: str = Field(...)
    clinical_status: Literal["active", "inactive", "resolved"] = "active"
    severity: Literal["mild", "moderate", "severe"] | None = None
    onset_date: date | None = None
    patient_id: str = Field(...)
    assessment_id: str | None = None


class CommunityResource(BaseVertex):
    """Community support resource."""
    
    _label = "CommunityResource"
    _fhir_resource_type = None
    _omop_table = None
    
    name: str = Field(...)
    description: str | None = None
    category: Literal["food", "housing", "transportation", "utility", "employment", "mental_health", "other"] = Field(...)
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    service_area: str | None = None
    is_active: bool = True
