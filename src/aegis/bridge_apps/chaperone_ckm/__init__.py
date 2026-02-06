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
try:
    from .service import ChaperoneCKMService
except (ImportError, AttributeError, TypeError) as e:
    ChaperoneCKMService = None

try:
    from .api import router as ckm_router
    # Ensure router exists and is not None
    if ckm_router is None:
        logger.warning("ckm_router is None, creating fallback router")
        from fastapi import APIRouter
        ckm_router = APIRouter()
except (ImportError, AttributeError, TypeError) as e:
    logger.warning(f"Failed to import ckm_router: {e}")
    try:
        from fastapi import APIRouter
        ckm_router = APIRouter()  # Fallback empty router
    except Exception:
        ckm_router = None

__all__ = [
    'ChaperoneCKMService',
    'ckm_router',
]
