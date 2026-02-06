"""
Chaperone CKM Bridge App - Chronic Kidney Disease Management

Patient-facing bridge app for CKD care management:
- Patient dashboard (eGFR trends, KFRE, care gaps)
- Vital logging (BP, weight)
- Care gap reminders
- Medication adherence tracking
- Personalized education
"""

# Graceful imports with comprehensive error handling
# Import router FIRST - it's safe even if service fails
ckm_router = None
ChaperoneCKMService = None

try:
    # Try to import router - this should always succeed
    from .api import router as ckm_router
except (ImportError, AttributeError, TypeError, SyntaxError, NameError) as e:
    # If router import fails, create fallback
    try:
        from fastapi import APIRouter
        ckm_router = APIRouter()  # Fallback empty router
    except Exception:
        ckm_router = None

try:
    from .service import ChaperoneCKMService
except (ImportError, AttributeError, TypeError, SyntaxError, NameError) as e:
    ChaperoneCKMService = None

__all__ = [
    'ChaperoneCKMService',
    'ckm_router',
]
