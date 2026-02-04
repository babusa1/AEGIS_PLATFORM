"""
AEGIS Clinical Module

Clinical data management:
- SDOH (Social Determinants of Health)
- Symptoms tracking
- Care gaps
"""

from aegis.clinical.sdoh import (
    SDOHDomain,
    SDOHRiskLevel,
    SDOHFactor,
    SDOHAssessment,
    SDOHSummary,
    SDOHService,
    SDOH_ICD10_CODES,
    router as sdoh_router,
)
from aegis.clinical.symptoms import (
    SymptomSeverity,
    SymptomCategory,
    Symptom,
    SymptomEntry,
    SymptomTracker,
    router as symptoms_router,
)

__all__ = [
    # SDOH
    "SDOHDomain",
    "SDOHRiskLevel",
    "SDOHFactor",
    "SDOHAssessment",
    "SDOHSummary",
    "SDOHService",
    "SDOH_ICD10_CODES",
    "sdoh_router",
    # Symptoms
    "SymptomSeverity",
    "SymptomCategory",
    "Symptom",
    "SymptomEntry",
    "SymptomTracker",
    "symptoms_router",
]
