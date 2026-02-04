"""
Denial Prediction Model

Predict claim denials before submission:
- Risk scoring
- Denial reason prediction
- Recommendations for prevention
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import math
import random

import structlog
from pydantic import BaseModel, Field

from aegis.ml.features import FeatureExtractor, ClaimFeatures

logger = structlog.get_logger(__name__)


# =============================================================================
# Denial Reasons (CARC/RARC codes)
# =============================================================================

class DenialReason(str, Enum):
    """Common denial reason categories."""
    # Authorization
    NO_PRIOR_AUTH = "no_prior_auth"
    AUTH_EXPIRED = "auth_expired"
    AUTH_MISMATCH = "auth_mismatch"
    
    # Eligibility
    NOT_COVERED = "not_covered"
    INACTIVE_COVERAGE = "inactive_coverage"
    OUT_OF_NETWORK = "out_of_network"
    
    # Medical Necessity
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    EXPERIMENTAL = "experimental"
    COSMETIC = "cosmetic"
    
    # Coding
    INVALID_CODE = "invalid_code"
    CODE_MISMATCH = "code_mismatch"
    BUNDLING = "bundling"
    MODIFIER_MISSING = "modifier_missing"
    
    # Documentation
    INSUFFICIENT_DOCS = "insufficient_docs"
    MISSING_INFO = "missing_info"
    
    # Timing
    TIMELY_FILING = "timely_filing"
    DUPLICATE = "duplicate"
    
    # Other
    COB_ISSUE = "cob_issue"
    PATIENT_LIABILITY = "patient_liability"
    OTHER = "other"


DENIAL_REASON_CARC = {
    DenialReason.NO_PRIOR_AUTH: ("27", "Prior authorization required"),
    DenialReason.AUTH_EXPIRED: ("27", "Authorization expired"),
    DenialReason.NOT_COVERED: ("96", "Non-covered charge(s)"),
    DenialReason.INACTIVE_COVERAGE: ("27", "Patient not eligible"),
    DenialReason.OUT_OF_NETWORK: ("B7", "Out of network provider"),
    DenialReason.NOT_MEDICALLY_NECESSARY: ("50", "Medical necessity not established"),
    DenialReason.INVALID_CODE: ("181", "Invalid procedure code"),
    DenialReason.CODE_MISMATCH: ("4", "Code inconsistent with modifier"),
    DenialReason.BUNDLING: ("97", "Benefit included in another service"),
    DenialReason.TIMELY_FILING: ("29", "Timely filing limit exceeded"),
    DenialReason.DUPLICATE: ("18", "Duplicate claim"),
    DenialReason.INSUFFICIENT_DOCS: ("16", "Missing information"),
}


# =============================================================================
# Prediction Models
# =============================================================================

class DenialPrediction(BaseModel):
    """Prediction result for a claim."""
    claim_id: str
    
    # Risk score (0-1)
    denial_probability: float
    risk_level: str  # low, medium, high, critical
    
    # Predicted reasons (with probabilities)
    predicted_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Top reason
    primary_reason: Optional[DenialReason] = None
    primary_reason_probability: float = 0.0
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    
    # Feature importance
    key_factors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Confidence
    confidence: float = 0.8
    model_version: str = "1.0.0"
    
    # Timing
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class DenialFeatures(BaseModel):
    """Features used for denial prediction."""
    claim_features: ClaimFeatures
    
    # Payer-specific denial rates
    payer_denial_rate: float = 0.0
    payer_code_denial_rate: float = 0.0  # For this CPT with this payer
    
    # Provider-specific
    provider_denial_rate: float = 0.0
    
    # Diagnosis-specific
    dx_denial_rate: float = 0.0
    
    # Combined risk factors
    risk_factors: List[str] = Field(default_factory=list)


# =============================================================================
# Denial Predictor
# =============================================================================

class DenialPredictor:
    """
    ML model for predicting claim denials.
    
    Features:
    - Gradient boosting model (simulated for demo)
    - Historical pattern analysis
    - Payer-specific rules
    - Recommendation engine
    """
    
    # Risk factor weights (simplified model)
    RISK_WEIGHTS = {
        "no_prior_auth": 0.25,
        "high_charge": 0.15,
        "out_of_network": 0.20,
        "untimely": 0.30,
        "complex_claim": 0.10,
        "high_denial_history": 0.15,
        "high_risk_dx": 0.10,
        "missing_modifier": 0.15,
    }
    
    # Payer-specific adjustments
    PAYER_ADJUSTMENTS = {
        "medicare": -0.05,  # Generally lower denial rate
        "medicaid": 0.05,
        "commercial": 0.0,
    }
    
    # High-risk CPT codes
    HIGH_RISK_CPTS = {
        "99215": 0.15,  # High-level E&M
        "99223": 0.12,  # Inpatient admission
        "43239": 0.20,  # EGD with biopsy
        "27447": 0.25,  # Total knee replacement
    }
    
    # High-denial diagnosis patterns
    HIGH_DENIAL_DX = {
        "M54": 0.15,   # Back pain
        "R10": 0.12,   # Abdominal pain
        "G43": 0.10,   # Migraine
    }
    
    def __init__(
        self,
        pool=None,
        model_path: str = None,
    ):
        self.pool = pool
        self.model_path = model_path
        self.feature_extractor = FeatureExtractor(pool)
        
        # Load trained model if available
        self._model = None
        if model_path:
            self._load_model(model_path)
    
    def _load_model(self, path: str):
        """Load trained model from file."""
        try:
            # Would load sklearn/xgboost model
            # self._model = joblib.load(path)
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
    
    async def predict(
        self,
        claim: dict,
        patient: dict = None,
        include_recommendations: bool = True,
    ) -> DenialPrediction:
        """
        Predict denial risk for a claim.
        
        Args:
            claim: Claim data
            patient: Patient data (optional)
            include_recommendations: Whether to include recommendations
            
        Returns:
            DenialPrediction with risk score and recommendations
        """
        # Extract features
        features = await self.feature_extractor.extract_features(
            claim=claim,
            patient=patient,
            historical=await self._get_historical_data(claim),
        )
        
        # Get payer-specific denial rates
        denial_features = await self._enrich_features(features)
        
        # Calculate risk score
        risk_score, risk_factors = self._calculate_risk_score(features, denial_features)
        
        # Predict denial reasons
        predicted_reasons = self._predict_reasons(features, denial_features)
        
        # Determine risk level
        risk_level = self._get_risk_level(risk_score)
        
        # Generate recommendations
        recommendations = []
        if include_recommendations:
            recommendations = self._generate_recommendations(
                features, predicted_reasons, risk_factors
            )
        
        # Get key factors
        key_factors = self._get_key_factors(risk_factors)
        
        # Primary reason
        primary_reason = None
        primary_prob = 0.0
        if predicted_reasons:
            primary_reason = DenialReason(predicted_reasons[0]["reason"])
            primary_prob = predicted_reasons[0]["probability"]
        
        return DenialPrediction(
            claim_id=features.claim_id,
            denial_probability=risk_score,
            risk_level=risk_level,
            predicted_reasons=predicted_reasons,
            primary_reason=primary_reason,
            primary_reason_probability=primary_prob,
            recommendations=recommendations,
            key_factors=key_factors,
            confidence=self._calculate_confidence(features),
        )
    
    async def predict_batch(
        self,
        claims: List[dict],
    ) -> List[DenialPrediction]:
        """Predict denial risk for multiple claims."""
        predictions = []
        for claim in claims:
            pred = await self.predict(claim)
            predictions.append(pred)
        return predictions
    
    async def _get_historical_data(self, claim: dict) -> dict:
        """Get historical denial data for context."""
        if not self.pool:
            return {
                "claims_count": 10,
                "denial_rate": 0.12,
                "denial_count": 1,
            }
        
        try:
            provider_npi = claim.get("provider_npi")
            payer_id = claim.get("payer_id")
            
            async with self.pool.acquire() as conn:
                # Get provider denial history
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_claims,
                        SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) as denied_claims
                    FROM claims
                    WHERE provider_npi = $1
                    AND created_at > NOW() - INTERVAL '12 months'
                """, provider_npi)
                
                if result:
                    total = result["total_claims"] or 1
                    denied = result["denied_claims"] or 0
                    return {
                        "claims_count": total,
                        "denial_rate": denied / total,
                        "denial_count": denied,
                    }
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
        
        return {"claims_count": 0, "denial_rate": 0.0, "denial_count": 0}
    
    async def _enrich_features(self, features: ClaimFeatures) -> DenialFeatures:
        """Enrich features with payer/provider-specific data."""
        # In production, would query actual denial rates
        payer_denial_rate = 0.08 + random.uniform(-0.02, 0.05)
        provider_denial_rate = 0.10 + random.uniform(-0.03, 0.05)
        
        # Check for high-risk patterns
        risk_factors = []
        
        if not features.has_prior_auth and features.total_charge > 1000:
            risk_factors.append("no_prior_auth_high_charge")
        
        if not features.provider_in_network:
            risk_factors.append("out_of_network")
        
        if not features.is_timely:
            risk_factors.append("untimely_filing")
        
        if features.complexity_score > 0.5:
            risk_factors.append("complex_claim")
        
        if features.prior_denial_rate > 0.15:
            risk_factors.append("high_denial_history")
        
        return DenialFeatures(
            claim_features=features,
            payer_denial_rate=payer_denial_rate,
            payer_code_denial_rate=self._get_code_denial_rate(features.primary_cpt),
            provider_denial_rate=provider_denial_rate,
            dx_denial_rate=self._get_dx_denial_rate(features.primary_dx),
            risk_factors=risk_factors,
        )
    
    def _get_code_denial_rate(self, cpt: str) -> float:
        """Get denial rate for specific CPT code."""
        return self.HIGH_RISK_CPTS.get(cpt, 0.08)
    
    def _get_dx_denial_rate(self, dx: str) -> float:
        """Get denial rate for diagnosis."""
        dx_prefix = dx[:3] if dx else ""
        return self.HIGH_DENIAL_DX.get(dx_prefix, 0.05)
    
    def _calculate_risk_score(
        self,
        features: ClaimFeatures,
        denial_features: DenialFeatures,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate overall denial risk score."""
        risk_factors = {}
        base_score = 0.05  # Base denial rate
        
        # Prior auth risk
        if not features.has_prior_auth:
            if features.total_charge > 5000:
                risk_factors["no_prior_auth"] = 0.25
            elif features.total_charge > 1000:
                risk_factors["no_prior_auth"] = 0.15
        
        # Network risk
        if not features.provider_in_network:
            risk_factors["out_of_network"] = 0.20
        
        # Timely filing risk
        if not features.is_timely:
            risk_factors["untimely"] = 0.30
        elif features.days_from_service > 60:
            risk_factors["approaching_timely_limit"] = 0.10
        
        # Complexity risk
        if features.complexity_score > 0.7:
            risk_factors["high_complexity"] = 0.12
        elif features.complexity_score > 0.5:
            risk_factors["moderate_complexity"] = 0.06
        
        # Historical risk
        if features.prior_denial_rate > 0.20:
            risk_factors["high_denial_history"] = 0.15
        elif features.prior_denial_rate > 0.10:
            risk_factors["elevated_denial_history"] = 0.08
        
        # CPT-specific risk
        cpt_risk = self._get_code_denial_rate(features.primary_cpt)
        if cpt_risk > 0.10:
            risk_factors["high_risk_procedure"] = cpt_risk
        
        # Diagnosis risk
        dx_risk = self._get_dx_denial_rate(features.primary_dx)
        if dx_risk > 0.08:
            risk_factors["high_risk_diagnosis"] = dx_risk
        
        # Payer adjustment
        payer_adj = self.PAYER_ADJUSTMENTS.get(features.payer_type, 0)
        
        # Calculate total score
        total_risk = base_score + sum(risk_factors.values()) + payer_adj
        
        # Apply sigmoid for smooth 0-1 output
        total_risk = 1 / (1 + math.exp(-5 * (total_risk - 0.3)))
        
        return min(0.95, max(0.02, total_risk)), risk_factors
    
    def _predict_reasons(
        self,
        features: ClaimFeatures,
        denial_features: DenialFeatures,
    ) -> List[Dict[str, Any]]:
        """Predict most likely denial reasons."""
        reasons = []
        
        # Prior auth issues
        if not features.has_prior_auth and features.total_charge > 1000:
            reasons.append({
                "reason": DenialReason.NO_PRIOR_AUTH.value,
                "probability": 0.65,
                "carc": DENIAL_REASON_CARC[DenialReason.NO_PRIOR_AUTH][0],
                "description": DENIAL_REASON_CARC[DenialReason.NO_PRIOR_AUTH][1],
            })
        
        # Out of network
        if not features.provider_in_network:
            reasons.append({
                "reason": DenialReason.OUT_OF_NETWORK.value,
                "probability": 0.70,
                "carc": DENIAL_REASON_CARC[DenialReason.OUT_OF_NETWORK][0],
                "description": DENIAL_REASON_CARC[DenialReason.OUT_OF_NETWORK][1],
            })
        
        # Timely filing
        if not features.is_timely:
            reasons.append({
                "reason": DenialReason.TIMELY_FILING.value,
                "probability": 0.90,
                "carc": DENIAL_REASON_CARC[DenialReason.TIMELY_FILING][0],
                "description": DENIAL_REASON_CARC[DenialReason.TIMELY_FILING][1],
            })
        
        # Medical necessity for high-cost claims
        if features.total_charge > 10000 and features.has_surgery:
            reasons.append({
                "reason": DenialReason.NOT_MEDICALLY_NECESSARY.value,
                "probability": 0.35,
                "carc": DENIAL_REASON_CARC[DenialReason.NOT_MEDICALLY_NECESSARY][0],
                "description": DENIAL_REASON_CARC[DenialReason.NOT_MEDICALLY_NECESSARY][1],
            })
        
        # Sort by probability
        reasons.sort(key=lambda x: x["probability"], reverse=True)
        
        return reasons
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level."""
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(
        self,
        features: ClaimFeatures,
        predicted_reasons: List[Dict],
        risk_factors: Dict[str, float],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Prior auth
        if "no_prior_auth" in risk_factors:
            recommendations.append(
                f"⚠️ Obtain prior authorization before submission. "
                f"Claim charge (${features.total_charge:,.2f}) exceeds threshold for this payer."
            )
        
        # Network
        if "out_of_network" in risk_factors:
            recommendations.append(
                "🏥 Provider is out-of-network. Consider single case agreement "
                "or verify patient has out-of-network benefits."
            )
        
        # Timely filing
        if "untimely" in risk_factors:
            recommendations.append(
                f"⏰ URGENT: Claim is past timely filing limit ({features.days_from_service} days). "
                "Submit immediately with documentation of delay reason."
            )
        elif "approaching_timely_limit" in risk_factors:
            recommendations.append(
                f"⏰ Warning: {features.days_from_service} days since service. "
                "Submit within 30 days to avoid timely filing denial."
            )
        
        # Documentation
        if features.complexity_score > 0.5:
            recommendations.append(
                "📋 Complex claim - ensure complete documentation including: "
                "operative notes, medical necessity letter, and supporting labs."
            )
        
        # High-risk procedure
        if features.has_surgery and features.total_charge > 5000:
            recommendations.append(
                "🔬 Surgical procedure over $5,000 - verify procedure codes match "
                "operative report and attach supporting documentation."
            )
        
        # Medical necessity
        if any(r["reason"] == "not_medically_necessary" for r in predicted_reasons):
            recommendations.append(
                "📝 Include medical necessity documentation: clinical notes, "
                "failed conservative treatments, and supporting evidence."
            )
        
        # General
        if not recommendations:
            recommendations.append(
                "✅ Claim appears to have low denial risk. "
                "Ensure all required fields are complete before submission."
            )
        
        return recommendations
    
    def _get_key_factors(self, risk_factors: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get key factors contributing to risk."""
        factors = []
        
        for factor, weight in sorted(risk_factors.items(), key=lambda x: -x[1]):
            factors.append({
                "factor": factor.replace("_", " ").title(),
                "impact": weight,
                "impact_pct": f"{weight * 100:.0f}%",
            })
        
        return factors[:5]  # Top 5 factors
    
    def _calculate_confidence(self, features: ClaimFeatures) -> float:
        """Calculate prediction confidence."""
        confidence = 0.85
        
        # More data = higher confidence
        if features.prior_claims_count > 50:
            confidence += 0.05
        elif features.prior_claims_count < 5:
            confidence -= 0.10
        
        # Complex claims have lower confidence
        if features.complexity_score > 0.7:
            confidence -= 0.05
        
        return min(0.95, max(0.60, confidence))


# =============================================================================
# API Functions
# =============================================================================

_predictor: Optional[DenialPredictor] = None


def get_denial_predictor() -> DenialPredictor:
    """Get global denial predictor."""
    global _predictor
    if _predictor is None:
        _predictor = DenialPredictor()
    return _predictor


async def predict_denial(claim: dict, patient: dict = None) -> DenialPrediction:
    """Predict denial for a claim."""
    predictor = get_denial_predictor()
    return await predictor.predict(claim, patient)
