"""
SDOH Domains and Data Models

Based on Gravity Project SDOH domains.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SDOHDomain(str, Enum):
    """Social Determinants of Health domains."""
    HOUSING = "housing_instability"
    FOOD = "food_insecurity"
    TRANSPORTATION = "transportation_insecurity"
    EDUCATION = "inadequate_education"
    EMPLOYMENT = "unemployment"
    FINANCIAL = "financial_strain"
    SOCIAL_SUPPORT = "social_isolation"
    INTIMATE_PARTNER = "intimate_partner_violence"
    STRESS = "stress"
    VETERAN = "veteran_status"
    DISABILITY = "disability_status"
    HEALTH_LITERACY = "inadequate_health_literacy"


class RiskLevel(str, Enum):
    """SDOH risk levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SDOHObservation:
    """Single SDOH observation/response."""
    domain: SDOHDomain
    code: str
    display: str
    value: str
    value_code: str | None = None
    risk_level: RiskLevel | None = None
    timestamp: datetime | None = None


@dataclass
class SDOHScreening:
    """SDOH screening result."""
    screening_id: str
    patient_id: str
    screening_date: datetime
    screening_tool: str  # PRAPARE, AHC-HRSN, etc.
    observations: list[SDOHObservation] = field(default_factory=list)
    overall_risk: RiskLevel | None = None
    referrals_needed: list[str] = field(default_factory=list)
    
    @property
    def domains_identified(self) -> list[SDOHDomain]:
        """Get domains with identified needs."""
        return list(set(o.domain for o in self.observations if o.risk_level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.URGENT)))


# LOINC codes for SDOH screening
SDOH_LOINC_CODES = {
    # Housing
    "71802-3": (SDOHDomain.HOUSING, "Housing status"),
    "93033-9": (SDOHDomain.HOUSING, "Housing instability"),
    
    # Food
    "88122-7": (SDOHDomain.FOOD, "Food insecurity risk"),
    "88123-5": (SDOHDomain.FOOD, "Worry about food"),
    "88124-3": (SDOHDomain.FOOD, "Food didn't last"),
    
    # Transportation
    "93030-5": (SDOHDomain.TRANSPORTATION, "Transportation needs"),
    
    # Education
    "82589-3": (SDOHDomain.EDUCATION, "Education level"),
    
    # Employment
    "67875-5": (SDOHDomain.EMPLOYMENT, "Employment status"),
    
    # Financial
    "76513-1": (SDOHDomain.FINANCIAL, "Financial resource strain"),
    
    # Social
    "93029-7": (SDOHDomain.SOCIAL_SUPPORT, "Social connections"),
    "93038-8": (SDOHDomain.SOCIAL_SUPPORT, "Social isolation"),
    
    # Stress
    "93025-5": (SDOHDomain.STRESS, "Stress level"),
}


# Screening tools
SCREENING_TOOLS = {
    "PRAPARE": "Protocol for Responding to and Assessing Patient Assets, Risks, and Experiences",
    "AHC-HRSN": "Accountable Health Communities Health-Related Social Needs",
    "WellRx": "WellRx Social Determinants",
    "CUSTOM": "Custom Screening Tool",
}
