"""
Oncolife Bridge App - Oncology Symptom Checker & Care Management

Integrates the Oncolife symptom checker engine with AEGIS Data Moat and Agentic Framework.

The symptom checker provides:
- Rule-based symptom triage (27 symptom modules)
- Emergency safety checks
- CTCAE-graded toxicity monitoring
- Integration with OncolifeAgent for care recommendations
"""

from .symptom_checker import SymptomCheckerService
from .api import router as oncolife_router

__all__ = ['SymptomCheckerService', 'oncolife_router']
