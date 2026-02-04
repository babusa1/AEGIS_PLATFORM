"""
Feature Engineering for Healthcare ML

Extract features from claims and clinical data.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Feature Models
# =============================================================================

class ClaimFeatures(BaseModel):
    """Features extracted from a claim for ML models."""
    claim_id: str
    
    # Claim characteristics
    claim_type: str  # professional, institutional
    place_of_service: str
    total_charge: float
    line_count: int
    
    # Diagnosis features
    primary_dx: str
    dx_count: int
    dx_categories: List[str] = Field(default_factory=list)
    has_chronic_condition: bool = False
    
    # Procedure features
    primary_cpt: str
    cpt_count: int
    cpt_categories: List[str] = Field(default_factory=list)
    has_surgery: bool = False
    has_evaluation: bool = False
    
    # Provider features
    provider_npi: str
    provider_specialty: str
    provider_in_network: bool = True
    
    # Patient features
    patient_age: int
    patient_gender: str
    has_prior_auth: bool = False
    
    # Payer features
    payer_id: str
    payer_type: str  # commercial, medicare, medicaid
    plan_type: str
    
    # Timing features
    days_from_service: int
    is_timely: bool = True
    submission_day_of_week: int
    submission_month: int
    
    # Historical features
    prior_claims_count: int = 0
    prior_denial_rate: float = 0.0
    prior_denial_count: int = 0
    
    # Complexity score
    complexity_score: float = 0.0


class FeatureExtractor:
    """
    Extract ML features from claim data.
    
    Handles:
    - Claim characteristics
    - Diagnosis/procedure categorization
    - Patient demographics
    - Historical patterns
    - Payer-specific features
    """
    
    # CPT category mappings
    CPT_CATEGORIES = {
        "evaluation": ["99201", "99202", "99203", "99204", "99205", 
                       "99211", "99212", "99213", "99214", "99215"],
        "surgery": ["1", "2", "3", "4", "5", "6"],  # CPT ranges starting with
        "radiology": ["7"],
        "pathology": ["8"],
        "medicine": ["9"],
    }
    
    # High-denial diagnoses
    HIGH_DENIAL_DX_PREFIXES = [
        "M54",  # Back pain
        "R10",  # Abdominal pain
        "J06",  # Upper respiratory
        "K21",  # GERD
        "F32",  # Depression
    ]
    
    def __init__(self, pool=None):
        self.pool = pool
    
    async def extract_features(
        self,
        claim: dict,
        patient: dict = None,
        historical: dict = None,
    ) -> ClaimFeatures:
        """Extract features from claim data."""
        
        # Basic claim features
        claim_type = claim.get("claim_type", "professional")
        lines = claim.get("lines", [])
        
        # Diagnosis features
        diagnoses = claim.get("diagnoses", [])
        primary_dx = diagnoses[0] if diagnoses else ""
        dx_categories = self._categorize_diagnoses(diagnoses)
        
        # Procedure features
        cpts = [line.get("cpt", "") for line in lines]
        primary_cpt = cpts[0] if cpts else ""
        cpt_categories = self._categorize_cpts(cpts)
        
        # Calculate charge
        total_charge = sum(line.get("charge", 0) for line in lines)
        
        # Patient features
        patient = patient or {}
        patient_age = self._calculate_age(patient.get("birth_date"))
        
        # Timing features
        service_date = claim.get("service_date")
        submission_date = claim.get("submission_date") or datetime.utcnow()
        days_from_service = self._days_between(service_date, submission_date)
        
        # Historical features
        historical = historical or {}
        
        # Calculate complexity
        complexity = self._calculate_complexity(
            dx_count=len(diagnoses),
            cpt_count=len(cpts),
            total_charge=total_charge,
            has_surgery="surgery" in cpt_categories,
        )
        
        return ClaimFeatures(
            claim_id=claim.get("id", ""),
            claim_type=claim_type,
            place_of_service=claim.get("place_of_service", "11"),
            total_charge=total_charge,
            line_count=len(lines),
            
            primary_dx=primary_dx,
            dx_count=len(diagnoses),
            dx_categories=dx_categories,
            has_chronic_condition=self._has_chronic(diagnoses),
            
            primary_cpt=primary_cpt,
            cpt_count=len(cpts),
            cpt_categories=cpt_categories,
            has_surgery="surgery" in cpt_categories,
            has_evaluation="evaluation" in cpt_categories,
            
            provider_npi=claim.get("provider_npi", ""),
            provider_specialty=claim.get("provider_specialty", ""),
            provider_in_network=claim.get("in_network", True),
            
            patient_age=patient_age,
            patient_gender=patient.get("gender", "unknown"),
            has_prior_auth=claim.get("has_prior_auth", False),
            
            payer_id=claim.get("payer_id", ""),
            payer_type=claim.get("payer_type", "commercial"),
            plan_type=claim.get("plan_type", "ppo"),
            
            days_from_service=days_from_service,
            is_timely=days_from_service <= 90,
            submission_day_of_week=submission_date.weekday() if isinstance(submission_date, datetime) else 0,
            submission_month=submission_date.month if isinstance(submission_date, datetime) else 1,
            
            prior_claims_count=historical.get("claims_count", 0),
            prior_denial_rate=historical.get("denial_rate", 0.0),
            prior_denial_count=historical.get("denial_count", 0),
            
            complexity_score=complexity,
        )
    
    def _categorize_diagnoses(self, diagnoses: List[str]) -> List[str]:
        """Categorize diagnoses into groups."""
        categories = set()
        
        for dx in diagnoses:
            dx = dx.upper().replace(".", "")
            
            if dx.startswith("E"):
                categories.add("endocrine")
            elif dx.startswith("I"):
                categories.add("cardiovascular")
            elif dx.startswith("J"):
                categories.add("respiratory")
            elif dx.startswith("K"):
                categories.add("digestive")
            elif dx.startswith("M"):
                categories.add("musculoskeletal")
            elif dx.startswith("N"):
                categories.add("genitourinary")
            elif dx.startswith("F"):
                categories.add("mental")
            elif dx.startswith("Z"):
                categories.add("preventive")
            elif dx.startswith("C"):
                categories.add("neoplasm")
        
        return list(categories)
    
    def _categorize_cpts(self, cpts: List[str]) -> List[str]:
        """Categorize CPT codes."""
        categories = set()
        
        for cpt in cpts:
            cpt = str(cpt)
            
            for category, prefixes in self.CPT_CATEGORIES.items():
                if category == "evaluation":
                    if cpt in prefixes:
                        categories.add(category)
                else:
                    if any(cpt.startswith(p) for p in prefixes):
                        categories.add(category)
        
        return list(categories)
    
    def _has_chronic(self, diagnoses: List[str]) -> bool:
        """Check for chronic conditions."""
        chronic_prefixes = ["E11", "I10", "J44", "I25", "N18"]  # Diabetes, HTN, COPD, CAD, CKD
        
        for dx in diagnoses:
            dx = dx.upper().replace(".", "")
            if any(dx.startswith(p) for p in chronic_prefixes):
                return True
        
        return False
    
    def _calculate_age(self, birth_date) -> int:
        """Calculate patient age."""
        if not birth_date:
            return 50  # Default
        
        if isinstance(birth_date, str):
            try:
                birth_date = datetime.fromisoformat(birth_date.replace("Z", ""))
            except:
                return 50
        
        today = datetime.utcnow()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        
        return max(0, min(120, age))
    
    def _days_between(self, date1, date2) -> int:
        """Calculate days between two dates."""
        if not date1 or not date2:
            return 0
        
        if isinstance(date1, str):
            try:
                date1 = datetime.fromisoformat(date1.replace("Z", ""))
            except:
                return 0
        
        if isinstance(date2, str):
            try:
                date2 = datetime.fromisoformat(date2.replace("Z", ""))
            except:
                return 0
        
        return abs((date2 - date1).days)
    
    def _calculate_complexity(
        self,
        dx_count: int,
        cpt_count: int,
        total_charge: float,
        has_surgery: bool,
    ) -> float:
        """Calculate claim complexity score (0-1)."""
        score = 0.0
        
        # Diagnosis complexity
        if dx_count > 5:
            score += 0.3
        elif dx_count > 2:
            score += 0.15
        
        # Procedure complexity
        if cpt_count > 5:
            score += 0.2
        elif cpt_count > 2:
            score += 0.1
        
        # Surgery flag
        if has_surgery:
            score += 0.2
        
        # Charge-based complexity
        if total_charge > 10000:
            score += 0.3
        elif total_charge > 5000:
            score += 0.2
        elif total_charge > 1000:
            score += 0.1
        
        return min(1.0, score)
    
    def to_feature_vector(self, features: ClaimFeatures) -> List[float]:
        """Convert features to numeric vector for ML model."""
        vector = [
            # Numeric features
            features.total_charge / 10000,  # Normalized
            features.line_count / 10,
            features.dx_count / 10,
            features.cpt_count / 10,
            features.patient_age / 100,
            features.days_from_service / 365,
            features.prior_claims_count / 100,
            features.prior_denial_rate,
            features.prior_denial_count / 10,
            features.complexity_score,
            
            # Boolean features (0/1)
            1.0 if features.has_chronic_condition else 0.0,
            1.0 if features.has_surgery else 0.0,
            1.0 if features.has_evaluation else 0.0,
            1.0 if features.provider_in_network else 0.0,
            1.0 if features.has_prior_auth else 0.0,
            1.0 if features.is_timely else 0.0,
            
            # Categorical features (one-hot encoded)
            1.0 if features.claim_type == "professional" else 0.0,
            1.0 if features.claim_type == "institutional" else 0.0,
            1.0 if features.payer_type == "commercial" else 0.0,
            1.0 if features.payer_type == "medicare" else 0.0,
            1.0 if features.payer_type == "medicaid" else 0.0,
            1.0 if features.patient_gender == "male" else 0.0,
            1.0 if features.patient_gender == "female" else 0.0,
        ]
        
        return vector
