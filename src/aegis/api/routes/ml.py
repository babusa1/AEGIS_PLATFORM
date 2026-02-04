"""
Machine Learning API Routes

Endpoints for:
- Denial Prediction
- Risk Scoring
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aegis.ml.denial_prediction import (
    DenialPredictor, DenialPrediction, get_denial_predictor, predict_denial
)
from aegis.ml.features import FeatureExtractor, ClaimFeatures

router = APIRouter(prefix="/ml", tags=["ml"])


# =============================================================================
# Request Models
# =============================================================================

class ClaimPredictionRequest(BaseModel):
    """Request for denial prediction."""
    claim: dict
    patient: Optional[dict] = None
    include_recommendations: bool = True


class BatchPredictionRequest(BaseModel):
    """Request for batch denial prediction."""
    claims: List[dict]


class ClaimData(BaseModel):
    """Structured claim data for prediction."""
    claim_id: str
    claim_type: str = "professional"
    place_of_service: str = "11"
    
    # Diagnoses
    diagnoses: List[str] = Field(default_factory=list)
    
    # Lines
    lines: List[dict] = Field(default_factory=list)
    
    # Provider
    provider_npi: Optional[str] = None
    provider_specialty: Optional[str] = None
    in_network: bool = True
    
    # Payer
    payer_id: Optional[str] = None
    payer_type: str = "commercial"
    plan_type: str = "ppo"
    
    # Auth
    has_prior_auth: bool = False
    
    # Dates
    service_date: Optional[str] = None
    submission_date: Optional[str] = None


# =============================================================================
# Prediction Endpoints
# =============================================================================

@router.post("/predict/denial")
async def predict_claim_denial(request: ClaimPredictionRequest):
    """
    Predict denial risk for a single claim.
    
    Returns:
    - Denial probability (0-1)
    - Risk level (low/medium/high/critical)
    - Predicted denial reasons with CARC codes
    - Actionable recommendations
    """
    predictor = get_denial_predictor()
    
    prediction = await predictor.predict(
        claim=request.claim,
        patient=request.patient,
        include_recommendations=request.include_recommendations,
    )
    
    return {
        "claim_id": prediction.claim_id,
        "denial_probability": round(prediction.denial_probability, 3),
        "risk_level": prediction.risk_level,
        "primary_reason": prediction.primary_reason.value if prediction.primary_reason else None,
        "primary_reason_probability": round(prediction.primary_reason_probability, 3),
        "predicted_reasons": prediction.predicted_reasons,
        "recommendations": prediction.recommendations,
        "key_factors": prediction.key_factors,
        "confidence": round(prediction.confidence, 3),
        "model_version": prediction.model_version,
    }


@router.post("/predict/denial/batch")
async def predict_batch_denial(request: BatchPredictionRequest):
    """
    Predict denial risk for multiple claims.
    
    Efficient batch processing for claim queues.
    """
    predictor = get_denial_predictor()
    
    predictions = await predictor.predict_batch(request.claims)
    
    # Summary statistics
    high_risk_count = len([p for p in predictions if p.risk_level in ["high", "critical"]])
    avg_probability = sum(p.denial_probability for p in predictions) / len(predictions)
    
    return {
        "total_claims": len(predictions),
        "high_risk_count": high_risk_count,
        "average_denial_probability": round(avg_probability, 3),
        "predictions": [
            {
                "claim_id": p.claim_id,
                "denial_probability": round(p.denial_probability, 3),
                "risk_level": p.risk_level,
                "primary_reason": p.primary_reason.value if p.primary_reason else None,
            }
            for p in predictions
        ],
    }


@router.post("/predict/denial/structured")
async def predict_structured_claim(claim: ClaimData):
    """
    Predict denial for structured claim data.
    
    Accepts properly typed claim data.
    """
    predictor = get_denial_predictor()
    
    prediction = await predictor.predict(
        claim=claim.dict(),
        include_recommendations=True,
    )
    
    return {
        "claim_id": prediction.claim_id,
        "denial_probability": round(prediction.denial_probability, 3),
        "risk_level": prediction.risk_level,
        "recommendations": prediction.recommendations,
    }


# =============================================================================
# Feature Endpoints
# =============================================================================

@router.post("/features/extract")
async def extract_features(claim: dict):
    """
    Extract ML features from a claim.
    
    Useful for understanding what features drive predictions.
    """
    extractor = FeatureExtractor()
    
    features = await extractor.extract_features(claim=claim)
    
    return {
        "claim_id": features.claim_id,
        "features": features.dict(),
        "feature_vector": extractor.to_feature_vector(features),
    }


# =============================================================================
# Risk Analysis Endpoints
# =============================================================================

@router.get("/risk/denial-reasons")
async def get_denial_reasons():
    """Get all possible denial reasons with CARC codes."""
    from aegis.ml.denial_prediction import DenialReason, DENIAL_REASON_CARC
    
    return {
        "denial_reasons": [
            {
                "code": reason.value,
                "carc": DENIAL_REASON_CARC.get(reason, ("", ""))[0],
                "description": DENIAL_REASON_CARC.get(reason, ("", ""))[1],
            }
            for reason in DenialReason
        ],
    }


@router.get("/risk/factors")
async def get_risk_factors():
    """Get all risk factors and their weights."""
    predictor = get_denial_predictor()
    
    return {
        "risk_factors": [
            {"factor": k, "weight": v}
            for k, v in predictor.RISK_WEIGHTS.items()
        ],
        "payer_adjustments": predictor.PAYER_ADJUSTMENTS,
        "high_risk_cpts": predictor.HIGH_RISK_CPTS,
    }


@router.post("/analyze/claim-queue")
async def analyze_claim_queue(claims: List[dict]):
    """
    Analyze a queue of claims for denial risk.
    
    Returns prioritized list with highest risk first.
    """
    predictor = get_denial_predictor()
    
    predictions = await predictor.predict_batch(claims)
    
    # Sort by risk (highest first)
    sorted_predictions = sorted(
        predictions,
        key=lambda p: p.denial_probability,
        reverse=True,
    )
    
    # Categorize
    critical = [p for p in sorted_predictions if p.risk_level == "critical"]
    high = [p for p in sorted_predictions if p.risk_level == "high"]
    medium = [p for p in sorted_predictions if p.risk_level == "medium"]
    low = [p for p in sorted_predictions if p.risk_level == "low"]
    
    return {
        "total_claims": len(claims),
        "risk_distribution": {
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
        },
        "prioritized_claims": [
            {
                "claim_id": p.claim_id,
                "risk_level": p.risk_level,
                "denial_probability": round(p.denial_probability, 3),
                "primary_reason": p.primary_reason.value if p.primary_reason else None,
                "top_recommendation": p.recommendations[0] if p.recommendations else None,
            }
            for p in sorted_predictions[:20]  # Top 20
        ],
        "action_required": len(critical) + len(high),
    }


# =============================================================================
# Readmission Prediction Endpoints
# =============================================================================

from aegis.ml.readmission_prediction import (
    ReadmissionPredictor,
    get_readmission_predictor,
    predict_readmission,
    get_high_risk_discharges,
)


class ReadmissionPredictionRequest(BaseModel):
    """Request for readmission prediction."""
    patient_id: str
    patient_data: Optional[dict] = None
    encounter_data: Optional[dict] = None
    conditions: Optional[List[dict]] = None
    medications: Optional[List[dict]] = None
    sdoh_data: Optional[dict] = None
    include_interventions: bool = True


class LACECalculationRequest(BaseModel):
    """Request for LACE score calculation."""
    length_of_stay_days: int = Field(..., ge=0, description="Hospital length of stay in days")
    emergency_admission: bool = Field(..., description="Whether admission was via ED/emergency")
    comorbidity_count: int = Field(..., ge=0, description="Number of active comorbidities")
    ed_visits_6_months: int = Field(..., ge=0, description="ED visits in past 6 months")


@router.post("/predict/readmission")
async def predict_patient_readmission(request: ReadmissionPredictionRequest):
    """
    Predict 30-day readmission risk for a patient.
    
    Uses:
    - LACE Index (validated clinical tool)
    - Condition-specific risk factors
    - SDOH risk assessment
    - Medication complexity
    
    Returns:
    - 30-day and 90-day readmission probabilities
    - Risk level (low/moderate/high/very_high)
    - LACE score breakdown
    - Key risk factors
    - Recommended interventions
    """
    predictor = get_readmission_predictor()
    
    prediction = await predictor.predict(
        patient_id=request.patient_id,
        patient_data=request.patient_data,
        encounter_data=request.encounter_data,
        conditions=request.conditions,
        medications=request.medications,
        sdoh_data=request.sdoh_data,
        include_interventions=request.include_interventions,
    )
    
    return {
        "patient_id": prediction.patient_id,
        "readmission_probability_30day": prediction.readmission_probability_30day,
        "readmission_probability_90day": prediction.readmission_probability_90day,
        "risk_level": prediction.risk_level.value,
        "lace_score": {
            "total_score": prediction.lace_score.total_score,
            "components": {
                "length_of_stay": {
                    "days": prediction.lace_score.length_of_stay_days,
                    "points": prediction.lace_score.length_of_stay_points,
                },
                "acuity": {
                    "emergency": prediction.lace_score.emergency_admission,
                    "points": prediction.lace_score.acuity_points,
                },
                "comorbidities": {
                    "count": prediction.lace_score.comorbidity_count,
                    "points": prediction.lace_score.comorbidity_points,
                },
                "ed_visits": {
                    "count": prediction.lace_score.ed_visits_6_months,
                    "points": prediction.lace_score.ed_visits_points,
                },
            },
        },
        "risk_factors": [
            {
                "factor": f.factor,
                "category": f.category,
                "impact": round(f.impact, 3),
                "description": f.description,
            }
            for f in prediction.risk_factors
        ],
        "high_risk_conditions": prediction.high_risk_conditions,
        "sdoh_factors": prediction.sdoh_risk_factors,
        "sdoh_risk_score": prediction.sdoh_risk_score,
        "recommended_interventions": [
            {
                "intervention": i.intervention,
                "priority": i.priority.value,
                "timeframe": i.timeframe,
                "responsible_party": i.responsible_party,
            }
            for i in prediction.recommended_interventions
        ],
        "care_plan_summary": prediction.care_plan_summary,
        "confidence": prediction.confidence,
    }


@router.post("/predict/readmission/batch")
async def predict_batch_readmission(patient_ids: List[str]):
    """
    Predict readmission risk for multiple patients.
    
    Useful for daily discharge risk screening.
    """
    predictor = get_readmission_predictor()
    
    predictions = await predictor.predict_batch(patient_ids)
    
    # Summary
    very_high = len([p for p in predictions if p.risk_level.value == "very_high"])
    high = len([p for p in predictions if p.risk_level.value == "high"])
    moderate = len([p for p in predictions if p.risk_level.value == "moderate"])
    low = len([p for p in predictions if p.risk_level.value == "low"])
    
    return {
        "total_patients": len(predictions),
        "risk_distribution": {
            "very_high": very_high,
            "high": high,
            "moderate": moderate,
            "low": low,
        },
        "high_risk_count": very_high + high,
        "predictions": [
            {
                "patient_id": p.patient_id,
                "risk_level": p.risk_level.value,
                "readmission_probability_30day": p.readmission_probability_30day,
                "lace_score": p.lace_score.total_score,
                "high_risk_conditions": p.high_risk_conditions,
                "urgent_interventions": len([i for i in p.recommended_interventions if i.priority.value in ["urgent", "high"]]),
            }
            for p in sorted(predictions, key=lambda x: x.readmission_probability_30day, reverse=True)
        ],
    }


@router.post("/calculate/lace")
async def calculate_lace(request: LACECalculationRequest):
    """
    Calculate LACE Index score directly.
    
    LACE Index is a validated tool for predicting 30-day readmission:
    - L: Length of stay
    - A: Acuity of admission (emergency)
    - C: Comorbidities (Charlson index)
    - E: ED visits in past 6 months
    
    Score interpretation:
    - 0-4: Low risk (~5% readmission)
    - 5-9: Moderate risk (~10% readmission)
    - 10-14: High risk (~20% readmission)
    - 15+: Very high risk (>30% readmission)
    """
    from aegis.ml.readmission_prediction import calculate_lace_score
    
    lace = calculate_lace_score(
        length_of_stay=request.length_of_stay_days,
        emergency_admission=request.emergency_admission,
        comorbidity_count=request.comorbidity_count,
        ed_visits_6_months=request.ed_visits_6_months,
    )
    
    return {
        "lace_score": {
            "total": lace.total_score,
            "components": {
                "L_length_of_stay": lace.length_of_stay_points,
                "A_acuity": lace.acuity_points,
                "C_comorbidity": lace.comorbidity_points,
                "E_ed_visits": lace.ed_visits_points,
            },
        },
        "risk_level": lace.risk_level.value,
        "readmission_probability": round(lace.readmission_probability, 3),
        "interpretation": {
            "0-4": "Low risk",
            "5-9": "Moderate risk",
            "10-14": "High risk",
            "15+": "Very high risk",
        },
    }


@router.get("/readmission/high-risk-discharges")
async def get_high_risk_discharge_patients(
    limit: int = Query(default=20, ge=1, le=100, description="Number of patients to return"),
    min_risk: float = Query(default=0.20, ge=0.0, le=1.0, description="Minimum risk threshold"),
):
    """
    Get recently discharged patients with high readmission risk.
    
    Useful for care management teams to identify patients
    needing immediate post-discharge interventions.
    """
    predictor = get_readmission_predictor()
    
    high_risk = await predictor.get_high_risk_patients(
        limit=limit,
        min_risk_score=min_risk,
    )
    
    return {
        "high_risk_patients": [
            {
                "patient_id": p.patient_id,
                "risk_level": p.risk_level.value,
                "readmission_probability_30day": p.readmission_probability_30day,
                "lace_score": p.lace_score.total_score,
                "discharge_date": p.discharge_date.isoformat() if p.discharge_date else None,
                "high_risk_conditions": p.high_risk_conditions,
                "urgent_interventions": [
                    i.intervention for i in p.recommended_interventions 
                    if i.priority.value == "urgent"
                ],
            }
            for p in high_risk
        ],
        "total_found": len(high_risk),
        "risk_threshold": min_risk,
    }
