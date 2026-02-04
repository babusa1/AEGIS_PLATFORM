"""
AEGIS Machine Learning Module

Healthcare ML models:
- Denial Prediction
- Readmission Risk
- Length of Stay Prediction
- Clinical Risk Scoring
"""

from aegis.ml.denial_prediction import (
    DenialPredictor,
    DenialPrediction,
    DenialFeatures,
    DenialReason,
    get_denial_predictor,
    predict_denial,
)
from aegis.ml.features import FeatureExtractor, ClaimFeatures
from aegis.ml.readmission_prediction import (
    ReadmissionPredictor,
    ReadmissionPrediction,
    ReadmissionRiskLevel,
    ReadmissionRiskFactor,
    ReadmissionIntervention,
    LACEScore,
    calculate_lace_score,
    get_readmission_predictor,
    predict_readmission,
    get_high_risk_discharges,
)

__all__ = [
    # Features
    "FeatureExtractor",
    "ClaimFeatures",
    # Denial Prediction
    "DenialPredictor",
    "DenialPrediction",
    "DenialFeatures",
    "DenialReason",
    "get_denial_predictor",
    "predict_denial",
    # Readmission Prediction
    "ReadmissionPredictor",
    "ReadmissionPrediction",
    "ReadmissionRiskLevel",
    "ReadmissionRiskFactor",
    "ReadmissionIntervention",
    "LACEScore",
    "calculate_lace_score",
    "get_readmission_predictor",
    "predict_readmission",
    "get_high_risk_discharges",
]
