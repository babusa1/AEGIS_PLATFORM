"""
Analytics & AI Domain Models

Models for AI/ML predictions and analytics:
- RiskScore (predictive risk assessments)
- CareGap (identified care gaps)
- AIRecommendation (agent recommendations)
- CohortMembership (population segmentation)

Critical for AEGIS agentic capabilities.
"""

from datetime import datetime, date
from typing import Literal, Any

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class RiskScore(BaseVertex):
    """
    Predictive risk score.
    
    FHIR: RiskAssessment
    """
    
    _label = "RiskScore"
    _fhir_resource_type = "RiskAssessment"
    _omop_table = None
    
    # Model info
    model_name: str = Field(..., description="Prediction model name")
    model_version: str | None = None
    model_type: Literal[
        "readmission", "mortality", "deterioration",
        "falls", "sepsis", "aki", "ckd_progression",
        "no_show", "cost", "utilization", "custom"
    ] = Field(..., description="Risk type")
    
    # Score
    score: float = Field(..., description="Risk score (0-1 or custom range)")
    score_percentile: float | None = Field(default=None, description="Percentile rank")
    
    # Risk level
    risk_level: Literal["low", "moderate", "high", "very_high"] = Field(..., description="Risk tier")
    
    # Confidence
    confidence: float | None = Field(default=None, description="Model confidence")
    
    # Prediction window
    prediction_window_days: int | None = Field(default=None, description="Days ahead")
    
    # Outcome probability
    probability: float | None = Field(default=None, description="Predicted probability")
    
    # Key factors
    top_factors: list[str] | None = Field(default=None, description="Contributing factors")
    factor_weights: dict[str, float] | None = None
    
    # Timing
    calculated_datetime: datetime = Field(..., description="When calculated")
    valid_until: datetime | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    
    # Source data
    data_version: str | None = None


class CareGap(BaseVertex):
    """
    Identified care gap.
    
    Critical for Care Gaps use case.
    """
    
    _label = "CareGap"
    _fhir_resource_type = None
    _omop_table = None
    
    # Gap identification
    measure_id: str = Field(..., description="Quality measure ID (e.g., NQF, CMS)")
    measure_name: str = Field(..., description="Measure name")
    measure_type: Literal[
        "preventive", "chronic", "screening", "immunization",
        "medication", "lab", "visit", "procedure", "other"
    ] = Field(..., description="Gap category")
    
    # Status
    status: Literal["open", "pending", "closed", "excluded"] = "open"
    
    # Gap details
    description: str | None = None
    due_date: date | None = Field(default=None, description="When due")
    overdue_days: int | None = None
    
    # Priority
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    
    # Evidence
    last_completed_date: date | None = None
    evidence_type: str | None = None
    evidence_id: str | None = None
    
    # Closure
    closed_date: date | None = None
    closed_reason: Literal["completed", "excluded", "refused", "contraindicated"] | None = None
    
    # Intervention
    intervention_type: str | None = None
    intervention_date: datetime | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    provider_id: str | None = None


class AIRecommendation(BaseVertex):
    """
    AI agent recommendation.
    
    Tracks agent-generated recommendations for audit.
    """
    
    _label = "AIRecommendation"
    _fhir_resource_type = None
    _omop_table = None
    
    # Agent info
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: Literal[
        "unified_view", "action", "insight",
        "denial_writer", "denial_auditor", 
        "care_navigator", "symptom_checker", "other"
    ] = Field(..., description="Agent type")
    
    # Recommendation
    recommendation_type: Literal[
        "alert", "order", "referral", "message",
        "care_plan_update", "documentation", "other"
    ] = Field(..., description="Recommendation type")
    
    description: str = Field(..., description="Recommendation text")
    rationale: str | None = Field(default=None, description="Reasoning/evidence")
    
    # Confidence
    confidence: float = Field(..., description="Agent confidence 0-1")
    
    # Priority
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    
    # Status
    status: Literal[
        "pending", "accepted", "modified", "rejected", "expired"
    ] = "pending"
    
    # Timing
    generated_datetime: datetime = Field(..., description="When generated")
    expires_datetime: datetime | None = None
    
    # Review
    reviewed_by_id: str | None = None
    reviewed_datetime: datetime | None = None
    review_notes: str | None = None
    
    # Outcome
    outcome_status: Literal["implemented", "partially_implemented", "not_implemented"] | None = None
    outcome_notes: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    
    # Related entities
    related_entity_type: str | None = None
    related_entity_id: str | None = None


class CohortMembership(BaseVertex):
    """
    Patient cohort/population membership.
    
    For population health segmentation.
    """
    
    _label = "CohortMembership"
    _fhir_resource_type = None
    _omop_table = "cohort"
    
    # Cohort
    cohort_id: str = Field(..., description="Cohort definition ID")
    cohort_name: str = Field(..., description="Cohort name")
    cohort_type: Literal[
        "disease", "risk", "program", "quality",
        "research", "operational", "custom"
    ] = Field(..., description="Cohort type")
    
    # Membership
    status: Literal["active", "inactive", "pending"] = "active"
    
    # Period
    start_date: date = Field(..., description="Membership start")
    end_date: date | None = None
    
    # Source
    source: Literal["rule", "ml", "manual"] = "rule"
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")


class QualityMeasure(BaseVertex):
    """
    Quality measure definition.
    
    Reference data for care gap tracking.
    """
    
    _label = "QualityMeasure"
    _fhir_resource_type = "Measure"
    _omop_table = None
    
    # Identifiers
    measure_id: str = Field(..., description="Measure ID (NQF, CMS, etc.)")
    measure_set: Literal["CMS", "NQF", "HEDIS", "MIPS", "custom"] = "CMS"
    
    # Info
    name: str = Field(..., description="Measure name")
    description: str | None = None
    
    # Type
    type: Literal["process", "outcome", "structure", "patient_reported"] = "process"
    
    # Domain
    domain: str | None = Field(default=None, description="Clinical domain")
    
    # Scoring
    scoring: Literal["proportion", "ratio", "continuous", "cohort"] = "proportion"
    
    # Reporting period
    reporting_period_days: int | None = None
    
    # Status
    status: Literal["draft", "active", "retired"] = "active"
    
    # Version
    version: str | None = None
    effective_date: date | None = None
