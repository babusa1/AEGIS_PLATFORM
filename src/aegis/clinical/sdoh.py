"""
Social Determinants of Health (SDOH) Module

Track and manage SDOH data for care gap analysis:
- Housing stability
- Food security
- Transportation access
- Social support
- Economic stability
- Education
- Healthcare access
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# SDOH Categories (Based on Healthy People 2030)
# =============================================================================

class SDOHDomain(str, Enum):
    """SDOH domain categories."""
    ECONOMIC_STABILITY = "economic_stability"
    EDUCATION_ACCESS = "education_access"
    HEALTHCARE_ACCESS = "healthcare_access"
    NEIGHBORHOOD_ENVIRONMENT = "neighborhood_environment"
    SOCIAL_COMMUNITY = "social_community"


class SDOHRiskLevel(str, Enum):
    """SDOH risk levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# SDOH screening questions and risk factors
SDOH_SCREENING = {
    SDOHDomain.ECONOMIC_STABILITY: {
        "factors": [
            {"code": "food_insecurity", "question": "In the past 12 months, did you worry about running out of food?", "weight": 0.8},
            {"code": "housing_cost_burden", "question": "In the past 12 months, was it difficult to pay for housing?", "weight": 0.7},
            {"code": "utility_insecurity", "question": "In the past 12 months, did you have trouble paying utility bills?", "weight": 0.5},
            {"code": "employment_instability", "question": "Are you currently unemployed and looking for work?", "weight": 0.6},
        ],
    },
    SDOHDomain.EDUCATION_ACCESS: {
        "factors": [
            {"code": "low_health_literacy", "question": "Do you have difficulty understanding health information?", "weight": 0.6},
            {"code": "language_barrier", "question": "Do you need help reading medical instructions?", "weight": 0.5},
        ],
    },
    SDOHDomain.HEALTHCARE_ACCESS: {
        "factors": [
            {"code": "no_primary_care", "question": "Do you have a primary care provider?", "weight": 0.7, "inverse": True},
            {"code": "no_transportation", "question": "Do you have reliable transportation to medical appointments?", "weight": 0.8, "inverse": True},
            {"code": "medication_cost_barrier", "question": "Have you skipped medications due to cost?", "weight": 0.9},
            {"code": "no_insurance", "question": "Do you have health insurance?", "weight": 0.8, "inverse": True},
        ],
    },
    SDOHDomain.NEIGHBORHOOD_ENVIRONMENT: {
        "factors": [
            {"code": "housing_instability", "question": "In the past 12 months, have you been homeless or worried about losing housing?", "weight": 0.9},
            {"code": "unsafe_neighborhood", "question": "Do you feel unsafe in your neighborhood?", "weight": 0.5},
            {"code": "limited_food_access", "question": "Is it difficult to access healthy food in your area?", "weight": 0.6},
        ],
    },
    SDOHDomain.SOCIAL_COMMUNITY: {
        "factors": [
            {"code": "lives_alone", "question": "Do you live alone?", "weight": 0.4},
            {"code": "social_isolation", "question": "Do you often feel lonely or isolated?", "weight": 0.6},
            {"code": "no_caregiver_support", "question": "Do you have someone who can help you if needed?", "weight": 0.5, "inverse": True},
            {"code": "domestic_violence", "question": "Do you feel safe at home?", "weight": 1.0, "inverse": True},
        ],
    },
}

# ICD-10 Z codes for SDOH
SDOH_ICD10_CODES = {
    "food_insecurity": "Z59.41",
    "housing_instability": "Z59.811",
    "homelessness": "Z59.00",
    "no_transportation": "Z59.82",
    "low_health_literacy": "Z55.0",
    "social_isolation": "Z60.2",
    "employment_instability": "Z56.0",
    "financial_hardship": "Z59.86",
    "lack_of_insurance": "Z59.7",
}


# =============================================================================
# SDOH Models
# =============================================================================

class SDOHFactor(BaseModel):
    """Individual SDOH factor."""
    code: str
    domain: SDOHDomain
    present: bool = False
    severity: SDOHRiskLevel = SDOHRiskLevel.LOW
    screening_date: Optional[datetime] = None
    notes: Optional[str] = None
    icd10_code: Optional[str] = None


class SDOHScreeningResponse(BaseModel):
    """Response to a single screening question."""
    factor_code: str
    response: bool
    response_text: Optional[str] = None
    screened_at: datetime = Field(default_factory=datetime.utcnow)


class SDOHAssessment(BaseModel):
    """Complete SDOH assessment for a patient."""
    patient_id: str
    tenant_id: str = "default"
    
    # Assessment info
    assessment_id: str
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    assessor: Optional[str] = None
    
    # Screening responses
    responses: List[SDOHScreeningResponse] = Field(default_factory=list)
    
    # Identified factors
    factors: List[SDOHFactor] = Field(default_factory=list)
    
    # Domain scores
    domain_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Overall
    overall_risk_score: float = 0.0
    overall_risk_level: SDOHRiskLevel = SDOHRiskLevel.LOW
    
    # Interventions
    recommended_interventions: List[str] = Field(default_factory=list)
    referrals: List[str] = Field(default_factory=list)


class SDOHSummary(BaseModel):
    """Summary of SDOH for patient care."""
    patient_id: str
    
    # Risk
    risk_level: SDOHRiskLevel
    risk_score: float
    
    # Active factors
    active_factors: List[str] = Field(default_factory=list)
    factor_count: int = 0
    
    # By domain
    domain_risks: Dict[str, str] = Field(default_factory=dict)
    
    # Care gaps
    care_gaps: List[str] = Field(default_factory=list)
    
    # Last assessment
    last_assessment_date: Optional[datetime] = None
    assessment_due: bool = False


# =============================================================================
# SDOH Service
# =============================================================================

class SDOHService:
    """
    Service for SDOH assessment and management.
    
    Features:
    - Screening questionnaire
    - Risk scoring
    - Care gap identification
    - Intervention recommendations
    - Community resource referrals
    """
    
    def __init__(self, pool=None):
        self.pool = pool
    
    async def get_screening_questions(
        self,
        domains: List[SDOHDomain] = None,
    ) -> Dict[str, List[dict]]:
        """
        Get SDOH screening questions.
        
        Args:
            domains: Specific domains to include (all if not specified)
            
        Returns:
            Questions organized by domain
        """
        questions = {}
        
        for domain, data in SDOH_SCREENING.items():
            if domains and domain not in domains:
                continue
            
            questions[domain.value] = [
                {
                    "code": f["code"],
                    "question": f["question"],
                    "inverse": f.get("inverse", False),
                }
                for f in data["factors"]
            ]
        
        return questions
    
    async def assess(
        self,
        patient_id: str,
        responses: List[SDOHScreeningResponse],
        tenant_id: str = "default",
        assessor: str = None,
    ) -> SDOHAssessment:
        """
        Perform SDOH assessment based on screening responses.
        
        Args:
            patient_id: Patient identifier
            responses: Screening question responses
            tenant_id: Tenant identifier
            assessor: Person conducting assessment
            
        Returns:
            Complete SDOH assessment
        """
        import uuid
        
        # Identify risk factors
        factors = []
        domain_scores = {d.value: 0.0 for d in SDOHDomain}
        domain_counts = {d.value: 0 for d in SDOHDomain}
        
        for response in responses:
            # Find factor info
            for domain, data in SDOH_SCREENING.items():
                for factor_info in data["factors"]:
                    if factor_info["code"] == response.factor_code:
                        # Check if factor is present
                        is_inverse = factor_info.get("inverse", False)
                        present = not response.response if is_inverse else response.response
                        
                        if present:
                            severity = self._calculate_severity(factor_info["weight"])
                            
                            factors.append(SDOHFactor(
                                code=factor_info["code"],
                                domain=domain,
                                present=True,
                                severity=severity,
                                screening_date=response.screened_at,
                                icd10_code=SDOH_ICD10_CODES.get(factor_info["code"]),
                            ))
                            
                            domain_scores[domain.value] += factor_info["weight"]
                        
                        domain_counts[domain.value] += 1
                        break
        
        # Normalize domain scores
        for domain in domain_scores:
            if domain_counts[domain] > 0:
                domain_scores[domain] = min(1.0, domain_scores[domain] / domain_counts[domain])
        
        # Calculate overall risk
        overall_score = sum(domain_scores.values()) / len(domain_scores) if domain_scores else 0
        overall_level = self._get_risk_level(overall_score)
        
        # Generate interventions
        interventions = self._generate_interventions(factors)
        referrals = self._generate_referrals(factors)
        
        return SDOHAssessment(
            patient_id=patient_id,
            tenant_id=tenant_id,
            assessment_id=str(uuid.uuid4()),
            assessor=assessor,
            responses=responses,
            factors=factors,
            domain_scores=domain_scores,
            overall_risk_score=round(overall_score, 3),
            overall_risk_level=overall_level,
            recommended_interventions=interventions,
            referrals=referrals,
        )
    
    async def get_patient_sdoh_summary(
        self,
        patient_id: str,
        tenant_id: str = "default",
    ) -> SDOHSummary:
        """
        Get SDOH summary for a patient.
        
        Args:
            patient_id: Patient identifier
            tenant_id: Tenant identifier
            
        Returns:
            SDOH summary
        """
        # In production, would load from database
        # For demo, return sample data
        
        if self.pool:
            try:
                async with self.pool.acquire() as conn:
                    # Would query sdoh_assessments table
                    pass
            except:
                pass
        
        # Sample data for demo
        return SDOHSummary(
            patient_id=patient_id,
            risk_level=SDOHRiskLevel.MODERATE,
            risk_score=0.35,
            active_factors=["no_transportation", "food_insecurity"],
            factor_count=2,
            domain_risks={
                "economic_stability": "moderate",
                "healthcare_access": "high",
                "social_community": "low",
            },
            care_gaps=[
                "Transportation assistance needed",
                "Food pantry referral recommended",
            ],
            assessment_due=True,
        )
    
    async def save_assessment(
        self,
        assessment: SDOHAssessment,
    ) -> bool:
        """Save SDOH assessment to database."""
        if not self.pool:
            logger.info("No database pool - assessment not saved")
            return True
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sdoh_assessments 
                    (id, patient_id, tenant_id, assessment_date, assessor, 
                     overall_risk_score, overall_risk_level, factors, domain_scores)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    assessment.assessment_id,
                    assessment.patient_id,
                    assessment.tenant_id,
                    assessment.assessment_date,
                    assessment.assessor,
                    assessment.overall_risk_score,
                    assessment.overall_risk_level.value,
                    [f.model_dump() for f in assessment.factors],
                    assessment.domain_scores,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to save assessment: {e}")
            return False
    
    def _calculate_severity(self, weight: float) -> SDOHRiskLevel:
        """Calculate severity based on factor weight."""
        if weight >= 0.9:
            return SDOHRiskLevel.CRITICAL
        elif weight >= 0.7:
            return SDOHRiskLevel.HIGH
        elif weight >= 0.5:
            return SDOHRiskLevel.MODERATE
        else:
            return SDOHRiskLevel.LOW
    
    def _get_risk_level(self, score: float) -> SDOHRiskLevel:
        """Get risk level from score."""
        if score >= 0.7:
            return SDOHRiskLevel.CRITICAL
        elif score >= 0.5:
            return SDOHRiskLevel.HIGH
        elif score >= 0.3:
            return SDOHRiskLevel.MODERATE
        else:
            return SDOHRiskLevel.LOW
    
    def _generate_interventions(
        self,
        factors: List[SDOHFactor],
    ) -> List[str]:
        """Generate intervention recommendations."""
        interventions = []
        
        factor_codes = {f.code for f in factors}
        
        if "food_insecurity" in factor_codes:
            interventions.append("Refer to food pantry or SNAP enrollment assistance")
        
        if "housing_instability" in factor_codes or "homelessness" in factor_codes:
            interventions.append("Refer to housing assistance program")
            interventions.append("Connect with social worker for housing resources")
        
        if "no_transportation" in factor_codes:
            interventions.append("Arrange medical transportation services")
            interventions.append("Consider telehealth for appropriate visits")
        
        if "medication_cost_barrier" in factor_codes:
            interventions.append("Review for patient assistance programs")
            interventions.append("Consider generic medication alternatives")
        
        if "social_isolation" in factor_codes or "lives_alone" in factor_codes:
            interventions.append("Refer to community support groups")
            interventions.append("Consider home health nursing visits")
        
        if "low_health_literacy" in factor_codes:
            interventions.append("Use simplified medication instructions")
            interventions.append("Provide health education materials at appropriate reading level")
        
        if "no_primary_care" in factor_codes:
            interventions.append("Assist with PCP selection and scheduling")
        
        return interventions
    
    def _generate_referrals(
        self,
        factors: List[SDOHFactor],
    ) -> List[str]:
        """Generate community resource referrals."""
        referrals = []
        
        factor_codes = {f.code for f in factors}
        
        if "food_insecurity" in factor_codes:
            referrals.append("Local food bank")
            referrals.append("Meals on Wheels")
            referrals.append("SNAP (food stamps) enrollment")
        
        if "housing_instability" in factor_codes:
            referrals.append("Housing authority")
            referrals.append("Emergency housing assistance")
        
        if "no_transportation" in factor_codes:
            referrals.append("Medicaid transportation benefit")
            referrals.append("Community ride programs")
        
        if "social_isolation" in factor_codes:
            referrals.append("Senior center programs")
            referrals.append("Faith community outreach")
        
        if "domestic_violence" in factor_codes:
            referrals.append("National Domestic Violence Hotline: 1-800-799-7233")
            referrals.append("Local domestic violence shelter")
        
        return referrals


# =============================================================================
# API Router
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/sdoh", tags=["Social Determinants of Health"])


class ScreeningResponseInput(PydanticBaseModel):
    """Input for a screening response."""
    factor_code: str
    response: bool
    response_text: Optional[str] = None


class AssessmentRequest(PydanticBaseModel):
    """Request for SDOH assessment."""
    patient_id: str
    tenant_id: str = "default"
    responses: List[ScreeningResponseInput]
    assessor: Optional[str] = None


@router.get("/screening-questions")
async def get_screening_questions(
    domains: str = Query(default=None, description="Comma-separated domains to include"),
):
    """
    Get SDOH screening questions.
    
    Based on CMS-approved SDOH screening tools.
    """
    service = SDOHService()
    
    domain_list = None
    if domains:
        domain_list = [SDOHDomain(d.strip()) for d in domains.split(",")]
    
    questions = await service.get_screening_questions(domain_list)
    
    return {
        "questions": questions,
        "domains": [d.value for d in SDOHDomain],
    }


@router.post("/assess")
async def perform_assessment(request: AssessmentRequest):
    """
    Perform SDOH assessment based on screening responses.
    
    Returns risk score, identified factors, and interventions.
    """
    service = SDOHService()
    
    # Convert inputs
    responses = [
        SDOHScreeningResponse(
            factor_code=r.factor_code,
            response=r.response,
            response_text=r.response_text,
        )
        for r in request.responses
    ]
    
    assessment = await service.assess(
        patient_id=request.patient_id,
        responses=responses,
        tenant_id=request.tenant_id,
        assessor=request.assessor,
    )
    
    return {
        "assessment_id": assessment.assessment_id,
        "patient_id": assessment.patient_id,
        "overall_risk_score": assessment.overall_risk_score,
        "overall_risk_level": assessment.overall_risk_level.value,
        "domain_scores": assessment.domain_scores,
        "factors": [
            {
                "code": f.code,
                "domain": f.domain.value,
                "severity": f.severity.value,
                "icd10_code": f.icd10_code,
            }
            for f in assessment.factors
        ],
        "recommended_interventions": assessment.recommended_interventions,
        "referrals": assessment.referrals,
    }


@router.get("/patient/{patient_id}")
async def get_patient_sdoh(
    patient_id: str,
    tenant_id: str = Query(default="default"),
):
    """Get SDOH summary for a patient."""
    service = SDOHService()
    
    summary = await service.get_patient_sdoh_summary(patient_id, tenant_id)
    
    return {
        "patient_id": summary.patient_id,
        "risk_level": summary.risk_level.value,
        "risk_score": summary.risk_score,
        "active_factors": summary.active_factors,
        "factor_count": summary.factor_count,
        "domain_risks": summary.domain_risks,
        "care_gaps": summary.care_gaps,
        "last_assessment_date": summary.last_assessment_date.isoformat() if summary.last_assessment_date else None,
        "assessment_due": summary.assessment_due,
    }


@router.get("/icd10-codes")
async def get_sdoh_icd10_codes():
    """Get ICD-10 Z codes for SDOH documentation."""
    return {
        "codes": [
            {"code": code, "factor": factor}
            for factor, code in SDOH_ICD10_CODES.items()
        ],
    }
