"""
Readmission Prediction Model

Predict 30-day hospital readmission risk:
- LACE index calculation
- Clinical risk factors
- Social determinants
- Intervention recommendations
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import math
import random

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Risk Factors and Categories
# =============================================================================

class ReadmissionRiskLevel(str, Enum):
    """Readmission risk levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class InterventionPriority(str, Enum):
    """Intervention priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    STANDARD = "standard"
    ROUTINE = "routine"


# High-risk conditions for readmission (ICD-10 prefixes)
HIGH_RISK_CONDITIONS = {
    "I50": {"name": "Heart Failure", "weight": 0.20, "intervention": "Cardiology follow-up within 7 days"},
    "J44": {"name": "COPD", "weight": 0.15, "intervention": "Pulmonology follow-up, smoking cessation"},
    "N18": {"name": "Chronic Kidney Disease", "weight": 0.12, "intervention": "Nephrology consult, medication review"},
    "E11": {"name": "Type 2 Diabetes", "weight": 0.10, "intervention": "Diabetes educator, glucose monitoring"},
    "I10": {"name": "Hypertension", "weight": 0.05, "intervention": "Blood pressure monitoring"},
    "F32": {"name": "Depression", "weight": 0.08, "intervention": "Behavioral health referral"},
    "A41": {"name": "Sepsis", "weight": 0.25, "intervention": "Infectious disease follow-up"},
    "J18": {"name": "Pneumonia", "weight": 0.15, "intervention": "Pulmonology follow-up"},
}

# SDOH risk factors
SDOH_RISK_FACTORS = {
    "lives_alone": 0.05,
    "no_transportation": 0.08,
    "food_insecurity": 0.06,
    "housing_instability": 0.10,
    "low_health_literacy": 0.07,
    "substance_use": 0.12,
    "no_primary_care": 0.08,
    "medication_nonadherence": 0.10,
}


# =============================================================================
# LACE Index Calculator
# =============================================================================

class LACEScore(BaseModel):
    """LACE Index components for readmission prediction."""
    # L: Length of Stay
    length_of_stay_days: int
    length_of_stay_points: int
    
    # A: Acuity (Emergency admission)
    emergency_admission: bool
    acuity_points: int
    
    # C: Comorbidities (Charlson Comorbidity Index)
    comorbidity_count: int
    comorbidity_points: int
    
    # E: ED visits in past 6 months
    ed_visits_6_months: int
    ed_visits_points: int
    
    # Total
    total_score: int
    risk_level: ReadmissionRiskLevel
    readmission_probability: float


def calculate_lace_score(
    length_of_stay: int,
    emergency_admission: bool,
    comorbidity_count: int,
    ed_visits_6_months: int,
) -> LACEScore:
    """
    Calculate LACE Index score.
    
    LACE Score interpretation:
    - 0-4: Low risk (5% readmission)
    - 5-9: Moderate risk (10% readmission)
    - 10-14: High risk (20% readmission)
    - 15+: Very high risk (30%+ readmission)
    """
    # L: Length of Stay points
    if length_of_stay <= 1:
        los_points = 1
    elif length_of_stay <= 2:
        los_points = 2
    elif length_of_stay <= 3:
        los_points = 3
    elif length_of_stay <= 6:
        los_points = 4
    elif length_of_stay <= 13:
        los_points = 5
    else:
        los_points = 7
    
    # A: Acuity points
    acuity_points = 3 if emergency_admission else 0
    
    # C: Comorbidity points (Charlson Index approximation)
    if comorbidity_count == 0:
        comorbidity_points = 0
    elif comorbidity_count <= 2:
        comorbidity_points = 1
    elif comorbidity_count <= 3:
        comorbidity_points = 2
    elif comorbidity_count <= 4:
        comorbidity_points = 3
    elif comorbidity_count <= 5:
        comorbidity_points = 4
    else:
        comorbidity_points = 5
    
    # E: ED visits points
    if ed_visits_6_months == 0:
        ed_points = 0
    elif ed_visits_6_months == 1:
        ed_points = 1
    elif ed_visits_6_months == 2:
        ed_points = 2
    elif ed_visits_6_months == 3:
        ed_points = 3
    else:
        ed_points = 4
    
    total_score = los_points + acuity_points + comorbidity_points + ed_points
    
    # Determine risk level
    if total_score <= 4:
        risk_level = ReadmissionRiskLevel.LOW
        probability = 0.05 + (total_score * 0.01)
    elif total_score <= 9:
        risk_level = ReadmissionRiskLevel.MODERATE
        probability = 0.10 + ((total_score - 5) * 0.02)
    elif total_score <= 14:
        risk_level = ReadmissionRiskLevel.HIGH
        probability = 0.20 + ((total_score - 10) * 0.02)
    else:
        risk_level = ReadmissionRiskLevel.VERY_HIGH
        probability = 0.30 + ((total_score - 15) * 0.02)
    
    probability = min(0.60, probability)
    
    return LACEScore(
        length_of_stay_days=length_of_stay,
        length_of_stay_points=los_points,
        emergency_admission=emergency_admission,
        acuity_points=acuity_points,
        comorbidity_count=comorbidity_count,
        comorbidity_points=comorbidity_points,
        ed_visits_6_months=ed_visits_6_months,
        ed_visits_points=ed_points,
        total_score=total_score,
        risk_level=risk_level,
        readmission_probability=probability,
    )


# =============================================================================
# Readmission Prediction Models
# =============================================================================

class ReadmissionRiskFactor(BaseModel):
    """Individual risk factor."""
    factor: str
    category: str  # clinical, sdoh, behavioral, medication
    impact: float
    description: str
    intervention: Optional[str] = None


class ReadmissionIntervention(BaseModel):
    """Recommended intervention."""
    intervention: str
    priority: InterventionPriority
    timeframe: str
    responsible_party: str
    evidence_strength: str  # high, moderate, low


class ReadmissionPrediction(BaseModel):
    """Full readmission prediction result."""
    patient_id: str
    
    # Risk scores
    readmission_probability_30day: float
    readmission_probability_90day: float
    risk_level: ReadmissionRiskLevel
    
    # LACE Index
    lace_score: LACEScore
    
    # Risk factors
    risk_factors: List[ReadmissionRiskFactor] = Field(default_factory=list)
    
    # Clinical summary
    primary_diagnoses: List[str] = Field(default_factory=list)
    high_risk_conditions: List[str] = Field(default_factory=list)
    
    # SDOH factors
    sdoh_risk_factors: List[str] = Field(default_factory=list)
    sdoh_risk_score: float = 0.0
    
    # Interventions
    recommended_interventions: List[ReadmissionIntervention] = Field(default_factory=list)
    care_plan_summary: str = ""
    
    # Timing
    discharge_date: Optional[datetime] = None
    predicted_readmission_window: str = ""
    
    # Confidence
    confidence: float = 0.8
    model_version: str = "1.0.0"
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Readmission Predictor
# =============================================================================

class ReadmissionPredictor:
    """
    ML model for predicting 30-day hospital readmission.
    
    Uses:
    - LACE Index (validated clinical tool)
    - Condition-specific risk factors
    - SDOH risk assessment
    - Medication complexity
    - Prior utilization patterns
    """
    
    def __init__(self, pool=None):
        self.pool = pool
    
    async def predict(
        self,
        patient_id: str,
        patient_data: dict = None,
        encounter_data: dict = None,
        conditions: List[dict] = None,
        medications: List[dict] = None,
        sdoh_data: dict = None,
        include_interventions: bool = True,
    ) -> ReadmissionPrediction:
        """
        Predict readmission risk for a patient.
        
        Args:
            patient_id: Patient identifier
            patient_data: Patient demographics
            encounter_data: Current/recent encounter
            conditions: Active conditions
            medications: Current medications
            sdoh_data: Social determinants data
            include_interventions: Whether to generate interventions
            
        Returns:
            ReadmissionPrediction with risk score and interventions
        """
        # Load data if not provided
        if not patient_data or not encounter_data:
            loaded = await self._load_patient_data(patient_id)
            patient_data = patient_data or loaded.get("patient", {})
            encounter_data = encounter_data or loaded.get("encounter", {})
            conditions = conditions or loaded.get("conditions", [])
            medications = medications or loaded.get("medications", [])
        
        # Calculate LACE score
        lace = self._calculate_lace(
            encounter_data,
            conditions,
            patient_data.get("ed_visits_6_months", 0),
        )
        
        # Analyze clinical risk factors
        clinical_factors = self._analyze_clinical_factors(conditions, medications)
        
        # Analyze SDOH factors
        sdoh_factors, sdoh_score = self._analyze_sdoh_factors(sdoh_data or {})
        
        # Calculate combined risk score
        base_prob = lace.readmission_probability
        clinical_adjustment = sum(f.impact for f in clinical_factors)
        sdoh_adjustment = sdoh_score
        
        # Combined probability with diminishing returns
        combined_prob = base_prob + (1 - base_prob) * (clinical_adjustment * 0.7 + sdoh_adjustment * 0.3)
        combined_prob = min(0.75, combined_prob)  # Cap at 75%
        
        # 90-day probability (higher)
        prob_90day = combined_prob * 1.3
        prob_90day = min(0.85, prob_90day)
        
        # Determine final risk level
        if combined_prob >= 0.40:
            risk_level = ReadmissionRiskLevel.VERY_HIGH
        elif combined_prob >= 0.25:
            risk_level = ReadmissionRiskLevel.HIGH
        elif combined_prob >= 0.15:
            risk_level = ReadmissionRiskLevel.MODERATE
        else:
            risk_level = ReadmissionRiskLevel.LOW
        
        # Get high-risk conditions
        high_risk = []
        for cond in conditions or []:
            code = cond.get("code", "")[:3]
            if code in HIGH_RISK_CONDITIONS:
                high_risk.append(HIGH_RISK_CONDITIONS[code]["name"])
        
        # Generate interventions
        interventions = []
        if include_interventions:
            interventions = self._generate_interventions(
                risk_level,
                clinical_factors,
                sdoh_factors,
                high_risk,
            )
        
        # Generate care plan summary
        care_plan = self._generate_care_plan(
            risk_level,
            interventions,
            high_risk,
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            bool(conditions),
            bool(medications),
            bool(sdoh_data),
        )
        
        return ReadmissionPrediction(
            patient_id=patient_id,
            readmission_probability_30day=round(combined_prob, 3),
            readmission_probability_90day=round(prob_90day, 3),
            risk_level=risk_level,
            lace_score=lace,
            risk_factors=clinical_factors,
            primary_diagnoses=[c.get("display", c.get("code", "")) for c in (conditions or [])[:5]],
            high_risk_conditions=high_risk,
            sdoh_risk_factors=sdoh_factors,
            sdoh_risk_score=round(sdoh_score, 3),
            recommended_interventions=interventions,
            care_plan_summary=care_plan,
            discharge_date=encounter_data.get("discharge_date"),
            predicted_readmission_window="0-30 days" if combined_prob > 0.20 else "30-90 days",
            confidence=confidence,
        )
    
    async def predict_batch(
        self,
        patient_ids: List[str],
    ) -> List[ReadmissionPrediction]:
        """Predict readmission for multiple patients."""
        predictions = []
        for patient_id in patient_ids:
            pred = await self.predict(patient_id)
            predictions.append(pred)
        return predictions
    
    async def get_high_risk_patients(
        self,
        limit: int = 20,
        min_risk_score: float = 0.20,
    ) -> List[ReadmissionPrediction]:
        """Get all high-risk patients for proactive intervention."""
        if not self.pool:
            # Return mock data
            return []
        
        try:
            async with self.pool.acquire() as conn:
                # Get recently discharged patients
                patients = await conn.fetch("""
                    SELECT DISTINCT p.id as patient_id
                    FROM patients p
                    JOIN encounters e ON p.id = e.patient_id
                    WHERE e.discharge_date IS NOT NULL
                    AND e.discharge_date > NOW() - INTERVAL '30 days'
                    LIMIT $1
                """, limit * 2)
                
                predictions = []
                for row in patients:
                    pred = await self.predict(row["patient_id"])
                    if pred.readmission_probability_30day >= min_risk_score:
                        predictions.append(pred)
                
                # Sort by risk
                predictions.sort(
                    key=lambda x: x.readmission_probability_30day,
                    reverse=True
                )
                
                return predictions[:limit]
                
        except Exception as e:
            logger.error(f"Failed to get high-risk patients: {e}")
            return []
    
    async def _load_patient_data(self, patient_id: str) -> dict:
        """Load patient data from database."""
        if not self.pool:
            # Return mock data for demo
            return {
                "patient": {
                    "id": patient_id,
                    "age": 68,
                    "ed_visits_6_months": 2,
                },
                "encounter": {
                    "encounter_type": "inpatient",
                    "admit_date": datetime.now() - timedelta(days=5),
                    "discharge_date": datetime.now(),
                    "emergency_admission": True,
                },
                "conditions": [
                    {"code": "I50.9", "display": "Heart Failure"},
                    {"code": "E11.9", "display": "Type 2 Diabetes"},
                    {"code": "I10", "display": "Hypertension"},
                ],
                "medications": [
                    {"display": "Lisinopril 10mg"},
                    {"display": "Metformin 500mg"},
                    {"display": "Furosemide 40mg"},
                    {"display": "Metoprolol 25mg"},
                    {"display": "Atorvastatin 20mg"},
                ],
            }
        
        try:
            async with self.pool.acquire() as conn:
                # Get patient
                patient = await conn.fetchrow("""
                    SELECT * FROM patients WHERE id = $1
                """, patient_id)
                
                # Get most recent encounter
                encounter = await conn.fetchrow("""
                    SELECT * FROM encounters 
                    WHERE patient_id = $1 
                    ORDER BY admit_date DESC LIMIT 1
                """, patient_id)
                
                # Get conditions
                conditions = await conn.fetch("""
                    SELECT * FROM conditions 
                    WHERE patient_id = $1 AND status = 'active'
                """, patient_id)
                
                # Get medications
                medications = await conn.fetch("""
                    SELECT * FROM medications 
                    WHERE patient_id = $1 AND status = 'active'
                """, patient_id)
                
                # Get ED visits
                ed_visits = await conn.fetchval("""
                    SELECT COUNT(*) FROM encounters
                    WHERE patient_id = $1
                    AND encounter_type = 'emergency'
                    AND admit_date > NOW() - INTERVAL '6 months'
                """, patient_id)
                
                patient_dict = dict(patient) if patient else {}
                patient_dict["ed_visits_6_months"] = ed_visits or 0
                
                return {
                    "patient": patient_dict,
                    "encounter": dict(encounter) if encounter else {},
                    "conditions": [dict(c) for c in conditions],
                    "medications": [dict(m) for m in medications],
                }
                
        except Exception as e:
            logger.error(f"Failed to load patient data: {e}")
            return {}
    
    def _calculate_lace(
        self,
        encounter: dict,
        conditions: List[dict],
        ed_visits: int,
    ) -> LACEScore:
        """Calculate LACE index."""
        # Length of stay
        admit = encounter.get("admit_date")
        discharge = encounter.get("discharge_date")
        
        if admit and discharge:
            if isinstance(admit, str):
                admit = datetime.fromisoformat(admit.replace("Z", "+00:00"))
            if isinstance(discharge, str):
                discharge = datetime.fromisoformat(discharge.replace("Z", "+00:00"))
            los = (discharge - admit).days
        else:
            los = 3  # Default
        
        # Emergency admission
        emergency = encounter.get("encounter_type") in ["emergency", "urgent"]
        emergency = emergency or encounter.get("emergency_admission", False)
        
        # Comorbidity count
        comorbidities = len(conditions) if conditions else 0
        
        return calculate_lace_score(
            length_of_stay=los,
            emergency_admission=emergency,
            comorbidity_count=comorbidities,
            ed_visits_6_months=ed_visits,
        )
    
    def _analyze_clinical_factors(
        self,
        conditions: List[dict],
        medications: List[dict],
    ) -> List[ReadmissionRiskFactor]:
        """Analyze clinical risk factors."""
        factors = []
        
        # Condition-based risks
        for cond in conditions or []:
            code = cond.get("code", "")[:3]
            if code in HIGH_RISK_CONDITIONS:
                risk_info = HIGH_RISK_CONDITIONS[code]
                factors.append(ReadmissionRiskFactor(
                    factor=risk_info["name"],
                    category="clinical",
                    impact=risk_info["weight"],
                    description=f"{risk_info['name']} increases readmission risk",
                    intervention=risk_info["intervention"],
                ))
        
        # Polypharmacy risk
        med_count = len(medications) if medications else 0
        if med_count >= 10:
            factors.append(ReadmissionRiskFactor(
                factor="Polypharmacy (10+ medications)",
                category="medication",
                impact=0.12,
                description="High medication count increases adverse event and readmission risk",
                intervention="Medication reconciliation and simplification review",
            ))
        elif med_count >= 6:
            factors.append(ReadmissionRiskFactor(
                factor="Multiple medications (6-9)",
                category="medication",
                impact=0.06,
                description="Multiple medications may affect adherence",
                intervention="Medication education and adherence support",
            ))
        
        # Multi-morbidity
        chronic_count = len([c for c in (conditions or []) if c.get("status") == "active"])
        if chronic_count >= 5:
            factors.append(ReadmissionRiskFactor(
                factor="Multi-morbidity (5+ conditions)",
                category="clinical",
                impact=0.10,
                description="Multiple chronic conditions increase care complexity",
                intervention="Care coordination and chronic disease management",
            ))
        
        return factors
    
    def _analyze_sdoh_factors(
        self,
        sdoh_data: dict,
    ) -> Tuple[List[str], float]:
        """Analyze social determinants of health."""
        factors = []
        score = 0.0
        
        for factor, weight in SDOH_RISK_FACTORS.items():
            if sdoh_data.get(factor, False):
                factors.append(factor.replace("_", " ").title())
                score += weight
        
        return factors, min(0.30, score)  # Cap SDOH contribution
    
    def _generate_interventions(
        self,
        risk_level: ReadmissionRiskLevel,
        clinical_factors: List[ReadmissionRiskFactor],
        sdoh_factors: List[str],
        high_risk_conditions: List[str],
    ) -> List[ReadmissionIntervention]:
        """Generate recommended interventions."""
        interventions = []
        
        # Universal interventions based on risk level
        if risk_level in [ReadmissionRiskLevel.HIGH, ReadmissionRiskLevel.VERY_HIGH]:
            interventions.append(ReadmissionIntervention(
                intervention="Schedule PCP follow-up within 7 days of discharge",
                priority=InterventionPriority.URGENT,
                timeframe="Within 7 days",
                responsible_party="Care Coordinator",
                evidence_strength="high",
            ))
            
            interventions.append(ReadmissionIntervention(
                intervention="Transitional care management (TCM) phone call within 48 hours",
                priority=InterventionPriority.URGENT,
                timeframe="Within 48 hours",
                responsible_party="Nurse Care Manager",
                evidence_strength="high",
            ))
        
        if risk_level == ReadmissionRiskLevel.VERY_HIGH:
            interventions.append(ReadmissionIntervention(
                intervention="Enroll in intensive outpatient care management program",
                priority=InterventionPriority.HIGH,
                timeframe="At discharge",
                responsible_party="Care Management Team",
                evidence_strength="high",
            ))
        
        # Condition-specific interventions
        if "Heart Failure" in high_risk_conditions:
            interventions.append(ReadmissionIntervention(
                intervention="Daily weight monitoring with patient callback protocol",
                priority=InterventionPriority.HIGH,
                timeframe="Daily starting at discharge",
                responsible_party="Heart Failure Nurse",
                evidence_strength="high",
            ))
            interventions.append(ReadmissionIntervention(
                intervention="Cardiology follow-up within 7 days",
                priority=InterventionPriority.HIGH,
                timeframe="Within 7 days",
                responsible_party="Cardiology",
                evidence_strength="high",
            ))
        
        if "COPD" in high_risk_conditions:
            interventions.append(ReadmissionIntervention(
                intervention="Pulmonary rehabilitation referral",
                priority=InterventionPriority.HIGH,
                timeframe="Within 14 days",
                responsible_party="Pulmonology",
                evidence_strength="moderate",
            ))
        
        # Medication interventions
        if any(f.category == "medication" for f in clinical_factors):
            interventions.append(ReadmissionIntervention(
                intervention="Pharmacist medication reconciliation and education",
                priority=InterventionPriority.HIGH,
                timeframe="Before discharge",
                responsible_party="Clinical Pharmacist",
                evidence_strength="high",
            ))
        
        # SDOH interventions
        if "No Transportation" in sdoh_factors:
            interventions.append(ReadmissionIntervention(
                intervention="Arrange medical transportation for follow-up appointments",
                priority=InterventionPriority.HIGH,
                timeframe="Before discharge",
                responsible_party="Social Worker",
                evidence_strength="moderate",
            ))
        
        if "Food Insecurity" in sdoh_factors:
            interventions.append(ReadmissionIntervention(
                intervention="Connect with food assistance programs and Meals on Wheels",
                priority=InterventionPriority.STANDARD,
                timeframe="Before discharge",
                responsible_party="Social Worker",
                evidence_strength="moderate",
            ))
        
        if "Lives Alone" in sdoh_factors:
            interventions.append(ReadmissionIntervention(
                intervention="Home health nursing assessment",
                priority=InterventionPriority.HIGH,
                timeframe="Within 72 hours",
                responsible_party="Home Health Agency",
                evidence_strength="high",
            ))
        
        return interventions
    
    def _generate_care_plan(
        self,
        risk_level: ReadmissionRiskLevel,
        interventions: List[ReadmissionIntervention],
        high_risk_conditions: List[str],
    ) -> str:
        """Generate care plan summary."""
        urgent = [i for i in interventions if i.priority == InterventionPriority.URGENT]
        high = [i for i in interventions if i.priority == InterventionPriority.HIGH]
        
        lines = [
            f"## Readmission Prevention Care Plan",
            f"**Risk Level:** {risk_level.value.upper()}",
            "",
        ]
        
        if high_risk_conditions:
            lines.append(f"**High-Risk Conditions:** {', '.join(high_risk_conditions)}")
            lines.append("")
        
        if urgent:
            lines.append("### Urgent Actions (Within 48 Hours)")
            for i in urgent:
                lines.append(f"- {i.intervention} ({i.responsible_party})")
            lines.append("")
        
        if high:
            lines.append("### High Priority Actions (Within 7 Days)")
            for i in high:
                lines.append(f"- {i.intervention} ({i.responsible_party})")
            lines.append("")
        
        lines.append("### Follow-up Schedule")
        lines.append("- TCM call: 48 hours post-discharge")
        lines.append("- PCP visit: 7 days post-discharge")
        if high_risk_conditions:
            lines.append(f"- Specialist visits: As indicated for {', '.join(high_risk_conditions[:2])}")
        
        return "\n".join(lines)
    
    def _calculate_confidence(
        self,
        has_conditions: bool,
        has_medications: bool,
        has_sdoh: bool,
    ) -> float:
        """Calculate prediction confidence."""
        confidence = 0.70  # Base confidence
        
        if has_conditions:
            confidence += 0.10
        if has_medications:
            confidence += 0.08
        if has_sdoh:
            confidence += 0.07
        
        return min(0.95, confidence)


# =============================================================================
# API Functions
# =============================================================================

_predictor: Optional[ReadmissionPredictor] = None


def get_readmission_predictor() -> ReadmissionPredictor:
    """Get global readmission predictor."""
    global _predictor
    if _predictor is None:
        _predictor = ReadmissionPredictor()
    return _predictor


async def predict_readmission(
    patient_id: str,
    patient_data: dict = None,
    encounter_data: dict = None,
) -> ReadmissionPrediction:
    """Predict readmission for a patient."""
    predictor = get_readmission_predictor()
    return await predictor.predict(
        patient_id,
        patient_data=patient_data,
        encounter_data=encounter_data,
    )


async def get_high_risk_discharges(
    limit: int = 20,
) -> List[ReadmissionPrediction]:
    """Get high-risk recently discharged patients."""
    predictor = get_readmission_predictor()
    return await predictor.get_high_risk_patients(limit=limit)
