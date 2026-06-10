"""
Patient Onboarding API Endpoints.

Handles the complete patient onboarding flow:
1. Fax/Referral Webhook - Receives incoming referrals
2. Onboarding Status - Check current onboarding step
3. Step Completion - Mark each step as complete
4. Manual Referral - Create referrals manually

Endpoints:
    POST /api/v1/onboarding/webhook/fax          - Receive fax webhook
    GET  /api/v1/onboarding/status               - Get onboarding status
    POST /api/v1/onboarding/complete/password    - Complete password step
    POST /api/v1/onboarding/complete/acknowledgement - Complete acknowledgement
    POST /api/v1/onboarding/complete/terms       - Complete terms/privacy
    POST /api/v1/onboarding/complete/reminders   - Complete reminder setup
    POST /api/v1/onboarding/referral/manual      - Create manual referral (admin)
"""

import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from db.session import get_patient_db, get_doctor_db
from routers.auth.dependencies import get_current_user
from core.config import settings
from core.logging import get_logger
from core.exceptions import ValidationError, NotFoundError

from services.onboarding_service import OnboardingService
from services.fax_service import FaxService, FaxProviderType

logger = get_logger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FaxWebhookPayload(BaseModel):
    """
    Payload from fax service webhook.
    
    Supports multiple fax providers:
    - Sinch (recommended)
    - Twilio
    - Phaxio
    - RingCentral
    - Generic format
    
    The service will automatically parse provider-specific fields.
    """
    # Generic fields (at least one identifier required)
    fax_id: Optional[str] = Field(None, description="Unique fax ID from provider")
    id: Optional[str] = Field(None, description="Alternative fax ID field")
    
    # Contact info
    from_number: Optional[str] = Field(None, description="Sender fax number")
    to_number: Optional[str] = Field(None, description="Receiving fax number")
    
    # Sinch specific
    fromNumber: Optional[str] = Field(None, description="Sinch: Sender number")
    toNumber: Optional[str] = Field(None, description="Sinch: Receiver number")
    
    # Timing
    received_at: Optional[str] = Field(None, description="ISO timestamp of receipt")
    timestamp: Optional[str] = Field(None, description="Alternative timestamp field")
    
    # Document info
    pages: Optional[int] = Field(None, description="Number of pages")
    pageCount: Optional[int] = Field(None, description="Alternative page count")
    
    # Document content (one of these should be provided)
    download_url: Optional[str] = Field(None, description="URL to download fax document")
    documentUrl: Optional[str] = Field(None, description="Sinch: Document URL")
    mediaUrl: Optional[str] = Field(None, description="Alternative media URL")
    MediaUrl: Optional[str] = Field(None, description="Twilio: Media URL")
    
    # Or base64 encoded content
    document: Optional[str] = Field(None, description="Base64 encoded document")
    content: Optional[str] = Field(None, description="Alternative base64 content")
    
    # If already in S3 (for direct S3 triggers)
    s3_bucket: Optional[str] = Field(None, description="S3 bucket with document")
    s3_key: Optional[str] = Field(None, description="S3 object key")
    
    class Config:
        extra = "allow"  # Allow additional provider-specific fields


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status check."""
    is_onboarded: bool
    current_step: Optional[str]
    steps: Optional[Dict[str, bool]]
    first_login_at: Optional[str]
    onboarding_completed_at: Optional[str]


class AcknowledgementRequest(BaseModel):
    """Request to complete acknowledgement step."""
    acknowledged: bool = Field(
        ...,
        description="Patient confirms understanding",
    )
    acknowledgement_text: str = Field(
        default="I understand that OncoLife is a symptom tracking tool and does not replace my care team or emergency services. In case of emergency, I will call 911.",
        description="The exact text acknowledged",
    )


class TermsPrivacyRequest(BaseModel):
    """Request to accept terms and privacy."""
    terms_accepted: bool = Field(..., description="Accept Terms & Conditions")
    privacy_accepted: bool = Field(..., description="Accept Privacy Policy")
    hipaa_acknowledged: bool = Field(
        default=True,
        description="Acknowledge HIPAA notice",
    )


class ReminderSetupRequest(BaseModel):
    """Request to set reminder preferences."""
    channel: str = Field(
        ...,
        description="Notification channel: 'email', 'sms', or 'both'",
        pattern="^(email|sms|both)$",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email for reminders (uses account email if not provided)",
    )
    phone: Optional[str] = Field(
        None,
        description="Phone for reminders (uses account phone if not provided)",
    )
    reminder_time: Optional[str] = Field(
        default="09:00",
        description="Daily reminder time in HH:MM format",
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    timezone: Optional[str] = Field(
        default="America/Los_Angeles",
        description="User's timezone",
    )


class ManualReferralRequest(BaseModel):
    """Request to create a manual referral."""
    # Patient info (required)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[date] = None
    sex: Optional[str] = None
    mrn: Optional[str] = None
    
    # Physician info (optional)
    physician_name: Optional[str] = None
    clinic_name: Optional[str] = None
    
    # Treatment info (optional)
    cancer_type: Optional[str] = None
    cancer_staging: Optional[str] = None
    chemo_plan_name: Optional[str] = None
    chemo_start_date: Optional[date] = None
    chemo_end_date: Optional[date] = None
    
    # Options
    send_welcome: bool = Field(
        default=True,
        description="Send welcome email/SMS",
    )


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.post("/webhook/fax")
async def receive_fax_webhook(
    payload: FaxWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_fax_provider: Optional[str] = Header(None, alias="X-Fax-Provider"),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Receive incoming fax webhook from fax service.
    
    This endpoint handles the complete fax reception flow:
    1. Receives webhook from fax provider (Sinch, Twilio, Phaxio, etc.)
    2. Downloads document from provider URL or decodes base64
    3. Uploads to S3 with KMS encryption
    4. Triggers OCR processing pipeline
    5. Creates patient account and sends welcome email
    
    Supported Providers:
    - Sinch (set X-Fax-Provider: sinch)
    - Twilio (set X-Fax-Provider: twilio)
    - Phaxio (set X-Fax-Provider: phaxio)
    - RingCentral (set X-Fax-Provider: ringcentral)
    - Generic (default)
    
    Security:
    - Validates webhook signature if FAX_WEBHOOK_SECRET is configured
    - Uses HTTPS only
    - Documents encrypted at rest with AWS KMS
    """
    # Determine fax ID for logging
    fax_id = payload.fax_id or payload.id or "unknown"
    logger.info(f"Received fax webhook: {fax_id} from provider: {x_fax_provider or 'unknown'}")
    
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Determine provider type
    provider = (x_fax_provider or "generic").lower()
    if provider not in [FaxProviderType.SINCH, FaxProviderType.TWILIO, 
                        FaxProviderType.PHAXIO, FaxProviderType.RINGCENTRAL]:
        provider = FaxProviderType.GENERIC
    
    # Check if document is already in S3 (direct S3 trigger) or needs to be fetched
    if payload.s3_bucket and payload.s3_key:
        # Document already in S3, process directly
        logger.info(f"Document already in S3: s3://{payload.s3_bucket}/{payload.s3_key}")
        
        async def process_existing_s3_document():
            try:
                onboarding_service = OnboardingService(patient_db, doctor_db)
                result = await onboarding_service.process_referral(
                    s3_bucket=payload.s3_bucket,
                    s3_key=payload.s3_key,
                    fax_number=payload.from_number or payload.fromNumber,
                )
                logger.info(f"Fax processed: {fax_id} -> {result}")
            except Exception as e:
                logger.error(f"Failed to process fax {fax_id}: {e}")
        
        background_tasks.add_task(process_existing_s3_document)
        
        return {
            "success": True,
            "message": "Fax received and queued for processing",
            "fax_id": fax_id,
        }
    
    # Document needs to be downloaded and uploaded to S3
    async def receive_and_process_fax():
        try:
            # Step 1: Receive fax (download/decode and upload to S3)
            fax_service = FaxService(patient_db)
            fax_result = await fax_service.receive_fax(
                provider=provider,
                payload=payload.model_dump(),
                raw_body=raw_body,
                signature=x_webhook_signature,
            )
            
            logger.info(f"Fax uploaded to S3: {fax_result}")
            
            # Step 2: Process with OCR and create patient
            onboarding_service = OnboardingService(patient_db, doctor_db)
            result = await onboarding_service.process_referral(
                s3_bucket=fax_result["s3_bucket"],
                s3_key=fax_result["s3_key"],
                fax_number=payload.from_number or payload.fromNumber,
            )
            
            logger.info(f"Fax fully processed: {fax_id} -> {result}")
            
        except Exception as e:
            logger.error(f"Failed to process fax {fax_id}: {e}", exc_info=True)
    
    background_tasks.add_task(receive_and_process_fax)
    
    return {
        "success": True,
        "message": "Fax received and queued for processing",
        "fax_id": fax_id,
        "provider": provider,
    }


@router.post("/webhook/fax/{provider}")
async def receive_provider_specific_webhook(
    provider: str,
    background_tasks: BackgroundTasks,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Provider-specific webhook endpoint.
    
    Use this if your fax provider doesn't support custom headers.
    
    Examples:
    - POST /api/v1/onboarding/webhook/fax/sinch
    - POST /api/v1/onboarding/webhook/fax/twilio
    - POST /api/v1/onboarding/webhook/fax/phaxio
    """
    raw_body = await request.body()
    
    # Parse JSON body
    import json
    try:
        payload_dict = json.loads(raw_body)
    except json.JSONDecodeError:
        # Try form-encoded (Twilio style)
        from urllib.parse import parse_qs
        payload_dict = {k: v[0] for k, v in parse_qs(raw_body.decode()).items()}
    
    fax_id = payload_dict.get("fax_id") or payload_dict.get("id") or payload_dict.get("FaxSid") or "unknown"
    logger.info(f"Received {provider} fax webhook: {fax_id}")
    
    async def receive_and_process_fax():
        try:
            fax_service = FaxService(patient_db)
            fax_result = await fax_service.receive_fax(
                provider=provider.lower(),
                payload=payload_dict,
                raw_body=raw_body,
                signature=x_webhook_signature,
            )
            
            onboarding_service = OnboardingService(patient_db, doctor_db)
            result = await onboarding_service.process_referral(
                s3_bucket=fax_result["s3_bucket"],
                s3_key=fax_result["s3_key"],
                fax_number=payload_dict.get("from_number") or payload_dict.get("From"),
            )
            
            logger.info(f"Fax fully processed: {fax_id} -> {result}")
            
        except Exception as e:
            logger.error(f"Failed to process fax {fax_id}: {e}", exc_info=True)
    
    background_tasks.add_task(receive_and_process_fax)
    
    return {
        "success": True,
        "message": "Fax received and queued for processing",
        "fax_id": fax_id,
        "provider": provider,
    }


# =============================================================================
# ONBOARDING STATUS & FLOW
# =============================================================================

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Get current onboarding status.
    
    Returns the current step in the onboarding flow and
    which steps have been completed.
    
    Used by frontend to:
    - Redirect to appropriate onboarding step
    - Show progress indicator
    - Skip completed steps
    """
    patient_uuid = current_user.get("sub") or current_user.get("uuid")
    
    if not patient_uuid:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    status = onboarding_service.get_onboarding_status(patient_uuid)
    
    return status


@router.post("/complete/password")
async def complete_password_step(
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Mark password reset step as complete.
    
    This is called after the patient successfully changes their
    temporary password through Cognito's NEW_PASSWORD_REQUIRED flow.
    
    The frontend should call this immediately after the password
    change API returns success.
    """
    patient_uuid = current_user.get("sub") or current_user.get("uuid")
    
    if not patient_uuid:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    status = onboarding_service.complete_password_reset(patient_uuid)
    
    return {
        "success": True,
        "message": "Password step completed",
        "next_step": status.get("current_step"),
    }


@router.post("/complete/acknowledgement")
async def complete_acknowledgement_step(
    request: AcknowledgementRequest,
    req: Request,
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Complete the acknowledgement step.
    
    The patient confirms they understand:
    - OncoLife does not replace their care team
    - OncoLife is not for emergencies (call 911)
    - They should follow their doctor's advice
    
    This is a legal requirement for the app.
    """
    if not request.acknowledged:
        raise HTTPException(
            status_code=400,
            detail="You must acknowledge the statement to continue",
        )
    
    patient_uuid = current_user.get("sub") or current_user.get("uuid")
    
    if not patient_uuid:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Get client IP for audit
    client_ip = req.client.host if req.client else None
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    status = onboarding_service.complete_acknowledgement(
        patient_uuid=patient_uuid,
        acknowledgement_text=request.acknowledgement_text,
        ip_address=client_ip,
    )
    
    return {
        "success": True,
        "message": "Acknowledgement completed",
        "next_step": status.get("current_step"),
    }


@router.post("/complete/terms")
async def complete_terms_step(
    request: TermsPrivacyRequest,
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Accept terms and privacy policy.
    
    The patient must accept:
    - Terms & Conditions
    - Privacy Policy (including HIPAA notice)
    
    Both must be accepted to continue.
    """
    patient_uuid = current_user.get("sub") or current_user.get("uuid")
    
    if not patient_uuid:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    
    try:
        status = onboarding_service.complete_terms_privacy(
            patient_uuid=patient_uuid,
            terms_accepted=request.terms_accepted,
            privacy_accepted=request.privacy_accepted,
            hipaa_acknowledged=request.hipaa_acknowledged,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "success": True,
        "message": "Terms and privacy accepted",
        "next_step": status.get("current_step"),
        "terms_version": settings.terms_version,
        "privacy_version": settings.privacy_version,
    }


@router.post("/complete/reminders")
async def complete_reminders_step(
    request: ReminderSetupRequest,
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Complete reminder setup and finalize onboarding.
    
    The patient sets their preferred:
    - Notification channel (email, SMS, or both)
    - Contact info (uses account info if not specified)
    - Reminder time (daily check-in reminder)
    - Timezone
    
    After this step, onboarding is complete and the patient
    is redirected to the main chat screen.
    """
    patient_uuid = current_user.get("sub") or current_user.get("uuid")
    
    if not patient_uuid:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    status = onboarding_service.complete_reminder_setup(
        patient_uuid=patient_uuid,
        channel=request.channel,
        email=request.email,
        phone=request.phone,
        reminder_time=request.reminder_time,
        timezone=request.timezone,
    )
    
    return {
        "success": True,
        "message": "Onboarding complete! Welcome to OncoLife.",
        "is_onboarded": True,
        "redirect_to": "/chat",
    }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

def require_admin_role(current_user: dict, doctor_db: Session) -> None:
    """
    Verify the current user has admin role.
    
    Args:
        current_user: The authenticated user dict
        doctor_db: Doctor database session to check staff roles
        
    Raises:
        HTTPException: If user is not an admin
    """
    from db.models.staff import StaffProfile
    
    user_uuid = current_user.get("sub") or current_user.get("uuid")
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user credentials"
        )
    
    # Check if user exists in staff profiles with admin role
    staff = doctor_db.query(StaffProfile).filter(
        StaffProfile.staff_uuid == user_uuid
    ).first()
    
    if not staff or staff.role != "admin":
        logger.warning(f"Non-admin user {user_uuid} attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation"
        )


@router.post("/referral/manual")
async def create_manual_referral(
    request: ManualReferralRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
    doctor_db: Session = Depends(get_doctor_db),
):
    """
    Create a referral manually (Admin only).
    
    Used when:
    - OCR fails and needs manual entry
    - Testing the onboarding flow
    - Bulk patient import
    
    Requires admin privileges.
    """
    # Verify admin role
    require_admin_role(current_user, doctor_db)
    
    if not request.email and not request.phone:
        raise HTTPException(
            status_code=400,
            detail="Either email or phone is required",
        )
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    
    patient_data = {
        "first_name": request.first_name,
        "last_name": request.last_name,
        "email": request.email,
        "phone": request.phone,
        "dob": request.dob,
        "sex": request.sex,
        "mrn": request.mrn,
    }
    
    physician_data = None
    if request.physician_name or request.clinic_name:
        physician_data = {
            "name": request.physician_name,
            "clinic": request.clinic_name,
        }
    
    treatment_data = None
    if request.cancer_type:
        treatment_data = {
            "cancer_type": request.cancer_type,
            "staging": request.cancer_staging,
            "plan_name": request.chemo_plan_name,
            "start_date": request.chemo_start_date,
            "end_date": request.chemo_end_date,
        }
    
    result = await onboarding_service.create_manual_referral(
        patient_data=patient_data,
        physician_data=physician_data,
        treatment_data=treatment_data,
        send_welcome=request.send_welcome,
    )
    
    return result


@router.get("/referral/{referral_uuid}")
async def get_referral(
    referral_uuid: UUID,
    current_user: dict = Depends(get_current_user),
    patient_db: Session = Depends(get_patient_db),
):
    """
    Get referral details (Admin only).
    
    Returns all extracted data from a referral for review.
    """
    from db.models.referral import PatientReferral
    
    referral = patient_db.query(PatientReferral).filter(
        PatientReferral.uuid == referral_uuid
    ).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    return {
        "uuid": str(referral.uuid),
        "status": referral.status,
        "created_at": referral.created_at.isoformat() if referral.created_at else None,
        "patient": {
            "first_name": referral.patient_first_name,
            "last_name": referral.patient_last_name,
            "email": referral.patient_email,
            "phone": referral.patient_phone,
            "dob": referral.patient_dob.isoformat() if referral.patient_dob else None,
            "sex": referral.patient_sex,
            "mrn": referral.patient_mrn,
        },
        "physician": {
            "name": referral.attending_physician_name,
            "clinic": referral.clinic_name,
        },
        "diagnosis": {
            "cancer_type": referral.cancer_type,
            "staging": referral.cancer_staging,
        },
        "treatment": {
            "plan_name": referral.chemo_plan_name,
            "start_date": referral.chemo_start_date.isoformat() if referral.chemo_start_date else None,
            "end_date": referral.chemo_end_date.isoformat() if referral.chemo_end_date else None,
            "current_cycle": referral.chemo_current_cycle,
            "total_cycles": referral.chemo_total_cycles,
        },
        "vitals": {
            "height_cm": referral.height_cm,
            "weight_kg": referral.weight_kg,
            "bmi": referral.bmi,
            "blood_pressure": referral.blood_pressure,
        },
        "history": {
            "past_medical": referral.past_medical_history,
            "past_surgical": referral.past_surgical_history,
            "medications": referral.current_medications,
        },
        "patient_uuid": str(referral.patient_uuid) if referral.patient_uuid else None,
        "fields_needing_review": referral.fields_needing_review,
    }

