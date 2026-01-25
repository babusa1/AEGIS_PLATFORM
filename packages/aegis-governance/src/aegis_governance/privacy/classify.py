"""Data Classification - HITRUST 07.a"""
from dataclasses import dataclass
from enum import Enum
from typing import Any
import re
import structlog

logger = structlog.get_logger(__name__)


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # PHI, PII
    HIGHLY_RESTRICTED = "highly_restricted"  # Substance, mental health


class DataCategory(str, Enum):
    GENERAL = "general"
    PHI = "phi"
    PII = "pii"
    FINANCIAL = "financial"
    MENTAL_HEALTH = "mental_health"
    SUBSTANCE_ABUSE = "substance_abuse"
    HIV = "hiv"
    GENETIC = "genetic"
    REPRODUCTIVE = "reproductive"


@dataclass
class ClassificationResult:
    sensitivity: SensitivityLevel
    categories: list[DataCategory]
    confidence: float
    reasons: list[str]
    requires_consent: bool = False
    requires_encryption: bool = True


class DataClassifier:
    """
    Automatic data classification.
    
    HITRUST 07.a: Asset classification
    SOC 2 Confidentiality: Data handling based on classification
    """
    
    # Keywords for sensitive categories
    CATEGORY_KEYWORDS = {
        DataCategory.MENTAL_HEALTH: ["depression", "anxiety", "bipolar", "schizophrenia",
                                     "psychiatric", "mental health", "therapy", "counseling"],
        DataCategory.SUBSTANCE_ABUSE: ["substance", "addiction", "alcohol", "drug abuse",
                                       "opioid", "rehab", "detox", "AA", "NA"],
        DataCategory.HIV: ["hiv", "aids", "viral load", "cd4", "antiretroviral"],
        DataCategory.GENETIC: ["genetic", "genome", "dna", "hereditary", "mutation", "brca"],
        DataCategory.REPRODUCTIVE: ["pregnancy", "abortion", "fertility", "ivf", "contraceptive"],
        DataCategory.FINANCIAL: ["payment", "credit card", "bank account", "billing", "insurance"],
    }
    
    # PHI identifiers
    PHI_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\bMRN[:\s#]*\d+\b',  # MRN
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
    ]
    
    def classify(self, content: str, context: dict | None = None) -> ClassificationResult:
        """Classify content for sensitivity level and categories."""
        categories = []
        reasons = []
        content_lower = content.lower()
        
        # Check for PHI patterns
        for pattern in self.PHI_PATTERNS:
            if re.search(pattern, content):
                categories.append(DataCategory.PHI)
                reasons.append("Contains PHI identifiers")
                break
        
        # Check category keywords
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if category not in categories:
                        categories.append(category)
                        reasons.append(f"Contains {category.value} content: {keyword}")
                    break
        
        # Determine sensitivity level
        if DataCategory.MENTAL_HEALTH in categories or DataCategory.SUBSTANCE_ABUSE in categories or \
           DataCategory.HIV in categories or DataCategory.GENETIC in categories:
            sensitivity = SensitivityLevel.HIGHLY_RESTRICTED
            requires_consent = True
        elif DataCategory.PHI in categories or DataCategory.PII in categories:
            sensitivity = SensitivityLevel.RESTRICTED
            requires_consent = True
        elif DataCategory.FINANCIAL in categories:
            sensitivity = SensitivityLevel.CONFIDENTIAL
            requires_consent = False
        elif categories:
            sensitivity = SensitivityLevel.INTERNAL
            requires_consent = False
        else:
            categories.append(DataCategory.GENERAL)
            sensitivity = SensitivityLevel.INTERNAL
            requires_consent = False
        
        return ClassificationResult(
            sensitivity=sensitivity,
            categories=categories,
            confidence=0.8 if reasons else 0.5,
            reasons=reasons,
            requires_consent=requires_consent,
            requires_encryption=sensitivity.value in ["restricted", "highly_restricted"]
        )
    
    def classify_field(self, field_name: str, value: Any) -> ClassificationResult:
        """Classify a specific field by name and value."""
        sensitive_fields = {
            "ssn": (SensitivityLevel.RESTRICTED, DataCategory.PII),
            "mrn": (SensitivityLevel.RESTRICTED, DataCategory.PHI),
            "dob": (SensitivityLevel.RESTRICTED, DataCategory.PHI),
            "date_of_birth": (SensitivityLevel.RESTRICTED, DataCategory.PHI),
            "diagnosis": (SensitivityLevel.RESTRICTED, DataCategory.PHI),
            "medication": (SensitivityLevel.RESTRICTED, DataCategory.PHI),
        }
        
        field_lower = field_name.lower()
        if field_lower in sensitive_fields:
            level, category = sensitive_fields[field_lower]
            return ClassificationResult(
                sensitivity=level,
                categories=[category],
                confidence=0.95,
                reasons=[f"Field '{field_name}' is classified as {category.value}"],
                requires_consent=True
            )
        
        # Check value content
        if isinstance(value, str):
            return self.classify(value)
        
        return ClassificationResult(
            sensitivity=SensitivityLevel.INTERNAL,
            categories=[DataCategory.GENERAL],
            confidence=0.5,
            reasons=["Default classification"]
        )
