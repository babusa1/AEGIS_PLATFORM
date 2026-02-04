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
