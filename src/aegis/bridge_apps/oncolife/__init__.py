"""
Oncolife Bridge App - Oncology Symptom Checker & Care Management

Integrates the Oncolife symptom checker engine with VeritOS Data Moat and Agentic Framework.

The symptom checker provides:
- Rule-based symptom triage (27 symptom modules)
- Emergency safety checks
- CTCAE-graded toxicity monitoring
- Integration with OncolifeAgent for care recommendations
"""

# Export symptom checker components
try:
    from .symptom_definitions import SYMPTOMS, SymptomDef, Question, Option
    from .symptom_engine import SymptomCheckerEngine
    from .constants import TriageLevel, InputType, SymptomCategory
except ImportError:
    # Graceful degradation if files not available
    SYMPTOMS = {}
    SymptomDef = None
    Question = None
    Option = None
    SymptomCheckerEngine = None
    TriageLevel = None
    InputType = None
    SymptomCategory = None

# Export service and router
try:
    from .symptom_checker import SymptomCheckerService
    from .api import router as oncolife_router
except (ImportError, AttributeError, TypeError) as e:
    SymptomCheckerService = None
    oncolife_router = None

__all__ = [
    'SYMPTOMS',
    'SymptomDef',
    'Question',
    'Option',
    'SymptomCheckerEngine',
    'TriageLevel',
    'InputType',
    'SymptomCategory',
    'SymptomCheckerService',
    'oncolife_router',
]





