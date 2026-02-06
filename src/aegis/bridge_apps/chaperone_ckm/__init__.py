"""
Chaperone CKM Bridge App - Chronic Kidney Disease Management

Patient-facing bridge app for CKD care management:
- Patient dashboard (eGFR trends, KFRE, care gaps)
- Vital logging (BP, weight)
- Care gap reminders
- Medication adherence tracking
- Personalized education
"""

try:
    from .service import ChaperoneCKMService
    from .api import router as ckm_router
except ImportError:
    ChaperoneCKMService = None
    ckm_router = None

__all__ = [
    'ChaperoneCKMService',
    'ckm_router',
]
