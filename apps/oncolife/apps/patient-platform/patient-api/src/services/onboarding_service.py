"""
Patient Onboarding Service.

This is the main orchestration service for the patient onboarding flow:
1. Receive and process referral faxes (OCR)
2. Create patient accounts in Cognito
3. Store data in normalized schema (providers, oncology_profile, medications)
4. Track per-field OCR confidence
5. Send welcome notifications
6. Handle multi-step first login

Schema Used:
    - patient_info: Patient demographics
    - providers: Physician/clinic information
    - oncology_profiles: Cancer & treatment details
    - medications: Normalized medication list
    - fax_ingestion_log: Fax processing audit
    - ocr_field_confidence: Per-field confidence tracking

Flow:
    Fax → OCR → Validate Confidence → Create Records → Send Welcome → Track Progress

Usage:
    from services import OnboardingService
    
    onboarding_service = OnboardingService(patient_db, doctor_db)
    result = await onboarding_service.process_referral(s3_bucket, s3_key)
"""

import secrets
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session

from core.config import settings
from core.logging import get_logger
from core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ExternalServiceError,
)

from db.models.referral import (
    PatientReferral,
    PatientOnboardingStatus,
    ReferralDocument,
    OnboardingNotificationLog,
    ReferralStatus,
    OnboardingStep,
)
from db.models.onboarding_schema import (
    Provider,
    OncologyProfile,
    Medication,
    FaxIngestionLog,
    OcrFieldConfidence,
    MedicationCategory,
    OcrFieldStatus,
    FaxProcessingStatus,
    OCR_CONFIDENCE_THRESHOLDS,
    get_confidence_threshold,
    is_field_acceptable,
)
from db.patient_models import PatientInfo, PatientConfigurations, PatientPhysicianAssociations

from services.ocr_service import OCRService, OCRResult, ExtractedField
from services.notification_service import NotificationService
from services.auth_service import AuthService
from services.medication_categorizer import categorize_medication, MedicationCategory as MedCat

logger = get_logger(__name__)


class OnboardingService:
    """
    Main service for patient onboarding.
    
    Orchestrates:
    - Referral processing (fax → OCR → normalized database)
    - Per-field confidence validation
    - Patient account creation (Cognito + local DB)
    - Welcome notifications (email + SMS)
    - Onboarding step tracking
    """
    
    def __init__(
        self,
        patient_db: Session,
        doctor_db: Optional[Session] = None,
        ocr_service: Optional[OCRService] = None,
        notification_service: Optional[NotificationService] = None,
        auth_service: Optional[AuthService] = None,
    ):
        """
        Initialize onboarding service.
        
        Args:
            patient_db: Patient database session
            doctor_db: Doctor database session (optional)
            ocr_service: OCR service instance (optional)
            notification_service: Notification service instance (optional)
            auth_service: Auth service instance (optional)
        """
        self.patient_db = patient_db
        self.doctor_db = doctor_db
        
        self.ocr_service = ocr_service or OCRService()
        self.notification_service = notification_service or NotificationService()
        self.auth_service = auth_service or AuthService(patient_db, doctor_db)
    
    # =========================================================================
    # REFERRAL PROCESSING
    # =========================================================================
    
    async def process_referral(
        self,
        s3_bucket: str,
        s3_key: str,
        fax_number: Optional[str] = None,
        fax_received_at: Optional[datetime] = None,
        fax_provider: Optional[str] = None,
        provider_fax_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a referral document from S3.
        
        Full flow:
        1. Create fax ingestion log
        2. Process document with OCR
        3. Store per-field confidence scores
        4. Validate confidence thresholds
        5. Create normalized records (provider, oncology_profile, medications)
        6. Create patient account
        7. Send welcome notifications
        
        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 object key
            fax_number: Source fax number (optional)
            fax_received_at: When fax was received (optional)
            fax_provider: Fax provider name (optional)
            provider_fax_id: Provider's fax ID (optional)
            
        Returns:
            Dict with referral status and patient info
        """
        logger.info(f"Processing referral: s3://{s3_bucket}/{s3_key}")
        
        # Step 1: Create fax ingestion log
        fax_log = FaxIngestionLog(
            source_number=fax_number,
            received_at=fax_received_at or datetime.utcnow(),
            fax_provider=fax_provider,
            provider_fax_id=provider_fax_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            ocr_status=FaxProcessingStatus.RECEIVED.value,
        )
        self.patient_db.add(fax_log)
        self.patient_db.flush()
        
        fax_id = fax_log.fax_id
        logger.info(f"Created fax log: {fax_id}")
        
        # Also create legacy referral record for compatibility
        referral = PatientReferral(
            status=ReferralStatus.PROCESSING.value,
            fax_number=fax_number,
            fax_received_at=fax_received_at or datetime.utcnow(),
        )
        self.patient_db.add(referral)
        self.patient_db.flush()
        
        referral_uuid = referral.uuid
        fax_log.referral_uuid = referral_uuid
        
        try:
            # Step 2: Create document record
            document = ReferralDocument(
                referral_uuid=referral_uuid,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
            )
            self.patient_db.add(document)
            
            # Step 3: Update status and process with OCR
            fax_log.ocr_status = FaxProcessingStatus.OCR_STARTED.value
            fax_log.ocr_started_at = datetime.utcnow()
            self.patient_db.flush()
            
            ocr_start = datetime.utcnow()
            ocr_result = await self.ocr_service.process_document(s3_bucket, s3_key)
            ocr_end = datetime.utcnow()
            
            # Update fax log with OCR results
            fax_log.ocr_status = FaxProcessingStatus.OCR_COMPLETED.value
            fax_log.ocr_completed_at = ocr_end
            fax_log.ocr_duration_ms = int((ocr_end - ocr_start).total_seconds() * 1000)
            fax_log.overall_confidence = ocr_result.overall_confidence
            fax_log.page_count = ocr_result.page_count
            
            # Update document with OCR results
            document.raw_ocr_text = ocr_result.raw_text
            document.ocr_confidence = ocr_result.overall_confidence
            document.page_count = ocr_result.page_count
            document.processed_at = datetime.utcnow()
            
            # Step 4: Store per-field confidence scores
            self._store_field_confidences(fax_log, ocr_result)
            
            # Step 5: Populate referral from OCR
            fax_log.ocr_status = FaxProcessingStatus.PARSING.value
            self._populate_referral_from_ocr(referral, ocr_result)
            
            referral.raw_extracted_data = ocr_result.to_dict()
            referral.extraction_confidence = ocr_result.overall_confidence
            
            # Step 6: Check if manual review is needed
            if ocr_result.requires_manual_review:
                fax_log.ocr_status = FaxProcessingStatus.REVIEW_NEEDED.value
                fax_log.manual_review_required = True
                fax_log.manual_review_reason = f"Fields with low confidence: {', '.join(ocr_result.fields_needing_review)}"
                
                referral.status = ReferralStatus.REVIEW_NEEDED.value
                referral.fields_needing_review = ocr_result.fields_needing_review
                
                self.patient_db.commit()
                
                logger.warning(f"Referral needs review: {referral_uuid}")
                return {
                    "success": False,
                    "fax_id": str(fax_id),
                    "referral_uuid": str(referral_uuid),
                    "status": ReferralStatus.REVIEW_NEEDED.value,
                    "requires_manual_review": True,
                    "fields_needing_review": ocr_result.fields_needing_review,
                    "overall_confidence": ocr_result.overall_confidence,
                }
            
            fax_log.ocr_status = FaxProcessingStatus.PARSED.value
            referral.status = ReferralStatus.PARSED.value
            self.patient_db.flush()
            
            # Step 7: Create normalized records (provider, oncology profile, medications)
            provider = self._create_or_get_provider(ocr_result)
            
            # Step 8: Create patient account
            patient_result = await self._create_patient_from_referral(referral)
            patient_uuid = patient_result["uuid"]
            
            # Step 9: Create oncology profile
            oncology_profile = self._create_oncology_profile(
                patient_uuid=patient_uuid,
                provider=provider,
                referral=referral,
                ocr_result=ocr_result,
            )
            
            # Step 10: Create medication records
            self._create_medications(
                patient_uuid=patient_uuid,
                oncology_profile=oncology_profile,
                ocr_result=ocr_result,
            )
            
            # Update fax log
            fax_log.ocr_status = FaxProcessingStatus.PATIENT_CREATED.value
            fax_log.patient_uuid = patient_uuid
            
            # Step 11: Send welcome notifications
            await self._send_welcome_notifications(referral)
            
            referral.status = ReferralStatus.WELCOME_SENT.value
            self.patient_db.commit()
            
            logger.info(f"Referral processed successfully: {referral_uuid}")
            
            return {
                "success": True,
                "fax_id": str(fax_id),
                "referral_uuid": str(referral_uuid),
                "patient_uuid": str(patient_uuid),
                "status": ReferralStatus.WELCOME_SENT.value,
                "patient_email": referral.patient_email,
                "overall_confidence": ocr_result.overall_confidence,
                "fields_extracted": len(ocr_result.extracted_fields),
            }
            
        except Exception as e:
            fax_log.ocr_status = FaxProcessingStatus.FAILED.value
            fax_log.error_message = str(e)
            referral.status = ReferralStatus.FAILED.value
            referral.status_message = str(e)
            self.patient_db.commit()
            
            logger.error(f"Referral processing failed: {referral_uuid} - {e}")
            raise
    
    def _store_field_confidences(
        self,
        fax_log: FaxIngestionLog,
        ocr_result: OCRResult,
    ) -> None:
        """Store per-field confidence scores for audit and review."""
        for field in ocr_result.extracted_fields:
            confidence_record = OcrFieldConfidence(
                fax_id=fax_log.fax_id,
                field_name=field.field_name,
                field_category=field.field_category,
                extracted_value=field.extracted_value,
                normalized_value=field.normalized_value,
                confidence_score=Decimal(str(round(field.confidence_score, 4))),
                confidence_threshold=Decimal(str(round(field.confidence_threshold, 4))),
                status=(
                    OcrFieldStatus.ACCEPTED.value 
                    if field.is_acceptable 
                    else OcrFieldStatus.REQUIRES_REVIEW.value
                ),
                accepted=field.is_acceptable,
                source_page=field.source_page,
            )
            self.patient_db.add(confidence_record)
    
    def _populate_referral_from_ocr(
        self,
        referral: PatientReferral,
        ocr_result: OCRResult,
    ) -> None:
        """Populate referral fields from OCR result."""
        # Patient demographics
        patient = ocr_result.patient_data
        referral.patient_first_name = patient.get("first_name")
        referral.patient_last_name = patient.get("last_name")
        referral.patient_email = patient.get("email")
        referral.patient_phone = patient.get("phone")
        referral.patient_mrn = patient.get("mrn")
        
        if patient.get("dob"):
            referral.patient_dob = patient["dob"]
        if patient.get("sex"):
            referral.patient_sex = patient["sex"]
        
        # Physician
        provider = ocr_result.provider_data
        referral.attending_physician_name = provider.get("name")
        referral.clinic_name = provider.get("clinic")
        
        # Diagnosis
        diagnosis = ocr_result.diagnosis_data
        referral.cancer_type = diagnosis.get("cancer_type")
        referral.cancer_staging = diagnosis.get("staging") or diagnosis.get("ajcc_stage")
        
        # Treatment
        treatment = ocr_result.treatment_data
        referral.chemo_plan_name = treatment.get("plan_name")
        if treatment.get("start_date"):
            referral.chemo_start_date = treatment["start_date"]
        if treatment.get("end_date"):
            referral.chemo_end_date = treatment["end_date"]
        referral.chemo_current_cycle = treatment.get("current_cycle")
        referral.chemo_total_cycles = treatment.get("total_cycles")
        referral.line_of_treatment = treatment.get("line_of_treatment")
        
        # Vitals
        vitals = ocr_result.vitals_data
        referral.bmi = vitals.get("bmi")
        referral.height_cm = vitals.get("height_cm")
        referral.weight_kg = vitals.get("weight_kg")
        referral.blood_pressure = vitals.get("blood_pressure")
        referral.pulse = vitals.get("pulse")
        referral.spo2 = vitals.get("spo2")
        
        # Medications as JSON
        if ocr_result.medications_data:
            referral.current_medications = ocr_result.medications_data
    
    def _create_or_get_provider(
        self,
        ocr_result: OCRResult,
    ) -> Optional[Provider]:
        """Create or retrieve provider record."""
        provider_data = ocr_result.provider_data
        
        if not provider_data.get("name"):
            return None
        
        # Check if provider already exists
        existing = self.patient_db.query(Provider).filter(
            Provider.full_name == provider_data["name"],
            Provider.clinic_name == provider_data.get("clinic"),
            Provider.is_deleted == False,
        ).first()
        
        if existing:
            return existing
        
        # Create new provider
        provider = Provider(
            full_name=provider_data["name"],
            clinic_name=provider_data.get("clinic"),
        )
        self.patient_db.add(provider)
        self.patient_db.flush()
        
        logger.info(f"Created provider: {provider.provider_id}")
        return provider
    
    def _create_oncology_profile(
        self,
        patient_uuid: str,
        provider: Optional[Provider],
        referral: PatientReferral,
        ocr_result: OCRResult,
    ) -> OncologyProfile:
        """Create oncology profile from referral data."""
        diagnosis = ocr_result.diagnosis_data
        treatment = ocr_result.treatment_data
        vitals = ocr_result.vitals_data
        
        profile = OncologyProfile(
            patient_id=patient_uuid,
            provider_id=provider.provider_id if provider else None,
            referral_uuid=referral.uuid,
            
            # Diagnosis
            cancer_type=diagnosis.get("cancer_type") or referral.cancer_type,
            cancer_stage=diagnosis.get("staging") or referral.cancer_staging,
            
            # Treatment
            line_of_treatment=treatment.get("line_of_treatment") or referral.line_of_treatment,
            chemo_plan_name=treatment.get("plan_name") or referral.chemo_plan_name,
            chemo_start_date=treatment.get("start_date") or referral.chemo_start_date,
            chemo_end_date=treatment.get("end_date") or referral.chemo_end_date,
            current_cycle=treatment.get("current_cycle") or referral.chemo_current_cycle,
            total_cycles=treatment.get("total_cycles") or referral.chemo_total_cycles,
            
            # Vitals
            bmi=Decimal(str(vitals.get("bmi"))) if vitals.get("bmi") else None,
            height_cm=vitals.get("height_cm"),
            weight_kg=vitals.get("weight_kg"),
            
            # History (not displayed to patient)
            past_medical_history=referral.past_medical_history,
            past_surgical_history=referral.past_surgical_history,
        )
        
        self.patient_db.add(profile)
        self.patient_db.flush()
        
        logger.info(f"Created oncology profile: {profile.profile_id}")
        return profile
    
    def _create_medications(
        self,
        patient_uuid: str,
        oncology_profile: OncologyProfile,
        ocr_result: OCRResult,
    ) -> List[Medication]:
        """Create normalized medication records with categorization."""
        medications = []
        
        for med_data in ocr_result.medications_data:
            med_name = med_data.get("name", "")
            if not med_name:
                continue
            
            # Get category from categorizer
            category, metadata = categorize_medication(med_name)
            
            medication = Medication(
                patient_id=patient_uuid,
                oncology_profile_id=oncology_profile.profile_id,
                medication_name=med_name,
                category=category.value,
                source="ocr",
                ocr_confidence=med_data.get("confidence", 0.85),
                active=True,
            )
            
            # Add details if available
            if med_data.get("details"):
                # Try to parse dose from details
                import re
                dose_match = re.search(r"(\d+\.?\d*)\s*(mg|g|ml|mcg)", med_data["details"], re.IGNORECASE)
                if dose_match:
                    medication.dose = f"{dose_match.group(1)} {dose_match.group(2)}"
            
            self.patient_db.add(medication)
            medications.append(medication)
        
        if medications:
            logger.info(f"Created {len(medications)} medication records")
        
        return medications
    
    def _validate_referral(self, referral: PatientReferral) -> List[str]:
        """
        Validate required fields are present.
        
        Returns:
            List of field names that need review
        """
        errors = []
        
        # Required fields
        if not referral.patient_first_name:
            errors.append("patient_first_name")
        if not referral.patient_last_name:
            errors.append("patient_last_name")
        if not referral.patient_email and not referral.patient_phone:
            errors.append("patient_email_or_phone")
        
        # Highly recommended fields
        if not referral.patient_dob:
            errors.append("patient_dob")
        if not referral.cancer_type:
            errors.append("cancer_type")
        if not referral.attending_physician_name:
            errors.append("attending_physician_name")
        
        return errors
    
    # =========================================================================
    # PATIENT ACCOUNT CREATION
    # =========================================================================
    
    async def _create_patient_from_referral(
        self,
        referral: PatientReferral,
    ) -> Dict[str, Any]:
        """
        Create patient account from referral data.
        
        Creates:
        1. Cognito user with temporary password
        2. PatientInfo record
        3. PatientConfigurations record
        4. PatientPhysicianAssociations record
        5. PatientOnboardingStatus record
        """
        logger.info(f"Creating patient from referral: {referral.uuid}")
        
        # Generate temporary password
        temp_password = self._generate_temp_password()
        
        # Prepare email (use provided or generate from phone)
        email = referral.patient_email
        if not email and referral.patient_phone:
            # Generate email from phone for Cognito (can be updated later)
            phone_clean = referral.patient_phone.replace("-", "").replace(" ", "")[-10:]
            email = f"{phone_clean}@patient.oncolife.local"
        
        if not email:
            raise ValidationError(
                message="Cannot create account: no email or phone number",
                field="patient_email",
            )
        
        # Create via Cognito
        auth_result = await self._create_cognito_user(
            email=email,
            first_name=referral.patient_first_name,
            last_name=referral.patient_last_name,
            temp_password=temp_password,
        )
        
        patient_uuid = auth_result["uuid"]
        
        # Update patient info with referral data
        patient = self.patient_db.query(PatientInfo).filter(
            PatientInfo.uuid == patient_uuid
        ).first()
        
        if patient:
            patient.phone_number = referral.patient_phone
            patient.dob = referral.patient_dob
            patient.sex = referral.patient_sex
            patient.mrn = referral.patient_mrn
            patient.disease_type = referral.cancer_type
        
        # Link referral to patient
        referral.patient_uuid = patient_uuid
        referral.cognito_user_id = patient_uuid
        referral.status = ReferralStatus.PATIENT_CREATED.value
        
        # Create onboarding status record
        onboarding_status = PatientOnboardingStatus(
            referral_uuid=referral.uuid,
            patient_uuid=patient_uuid,
            current_step=OnboardingStep.PASSWORD_RESET.value,
        )
        self.patient_db.add(onboarding_status)
        
        self.patient_db.flush()
        
        logger.info(f"Patient created: {patient_uuid}")
        
        return {
            "uuid": patient_uuid,
            "email": email,
            "temp_password": temp_password,
        }
    
    async def _create_cognito_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        temp_password: str,
    ) -> Dict[str, Any]:
        """Create Cognito user with temporary password."""
        import boto3
        from botocore.exceptions import ClientError
        
        cognito_client = boto3.client(
            "cognito-idp",
            region_name=settings.aws_region,
        )
        
        try:
            response = cognito_client.admin_create_user(
                UserPoolId=settings.cognito_user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "given_name", "Value": first_name},
                    {"Name": "family_name", "Value": last_name},
                ],
                TemporaryPassword=temp_password,
                ForceAliasCreation=False,
                MessageAction="SUPPRESS",  # We send our own welcome email
            )
            
            user_sub = None
            for attr in response["User"]["Attributes"]:
                if attr["Name"] == "sub":
                    user_sub = attr["Value"]
                    break
            
            if not user_sub:
                raise ExternalServiceError(
                    message="Cognito user created but UUID not returned",
                    service_name="Cognito",
                )
            
            # Create local database records
            self._create_patient_records(
                user_sub=user_sub,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            
            return {"uuid": user_sub, "email": email}
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            
            if error_code == "UsernameExistsException":
                raise ConflictError(
                    message=f"A patient with email {email} already exists",
                    resource_type="Patient",
                    resource_id=email,
                )
            
            raise ExternalServiceError(
                message=f"Failed to create Cognito user: {error_message}",
                service_name="Cognito",
            )
    
    def _create_patient_records(
        self,
        user_sub: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> None:
        """Create patient database records."""
        # Check if already exists
        existing = self.patient_db.query(PatientInfo).filter(
            PatientInfo.uuid == user_sub
        ).first()
        
        if existing:
            return
        
        # Create patient info
        patient = PatientInfo(
            uuid=user_sub,
            email_address=email,
            first_name=first_name,
            last_name=last_name,
        )
        self.patient_db.add(patient)
        
        # Create configuration
        config = PatientConfigurations(uuid=user_sub)
        self.patient_db.add(config)
        
        # Create physician association (use defaults)
        association = PatientPhysicianAssociations(
            patient_uuid=user_sub,
            physician_uuid=AuthService.DEFAULT_PHYSICIAN_UUID,
            clinic_uuid=AuthService.DEFAULT_CLINIC_UUID,
        )
        self.patient_db.add(association)
    
    def _generate_temp_password(self, length: int = None) -> str:
        """
        Generate a secure temporary password.
        
        Meets Cognito requirements:
        - At least 8 characters
        - Contains uppercase
        - Contains lowercase
        - Contains number
        - Contains special character
        """
        length = length or settings.onboarding_temp_password_length
        
        # Ensure minimum requirements
        password_chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*"),
        ]
        
        # Fill remaining with mix
        remaining = length - len(password_chars)
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password_chars.extend(secrets.choice(all_chars) for _ in range(remaining))
        
        # Shuffle
        secrets.SystemRandom().shuffle(password_chars)
        
        return "".join(password_chars)
    
    # =========================================================================
    # WELCOME NOTIFICATIONS
    # =========================================================================
    
    async def _send_welcome_notifications(
        self,
        referral: PatientReferral,
    ) -> None:
        """Send welcome email and SMS."""
        # Get temp password (stored during creation)
        temp_password = self._generate_temp_password()  # Regenerate for demo
        
        # Get onboarding status
        onboarding = self.patient_db.query(PatientOnboardingStatus).filter(
            PatientOnboardingStatus.referral_uuid == referral.uuid
        ).first()
        
        # Send email
        if referral.patient_email:
            try:
                result = await self.notification_service.send_welcome_email(
                    email=referral.patient_email,
                    first_name=referral.patient_first_name,
                    temp_password=temp_password,
                    physician_name=referral.attending_physician_name,
                )
                
                if onboarding:
                    onboarding.welcome_email_sent = True
                    onboarding.welcome_email_sent_at = datetime.utcnow()
                
                # Log notification
                self._log_notification(
                    patient_uuid=referral.patient_uuid,
                    referral_uuid=referral.uuid,
                    notification_type="welcome",
                    channel="email",
                    recipient=referral.patient_email,
                    status="sent",
                    message_id=result.get("message_id"),
                )
                
            except Exception as e:
                logger.error(f"Failed to send welcome email: {e}")
                self._log_notification(
                    patient_uuid=referral.patient_uuid,
                    referral_uuid=referral.uuid,
                    notification_type="welcome",
                    channel="email",
                    recipient=referral.patient_email,
                    status="failed",
                    status_message=str(e),
                )
        
        # Send SMS
        if referral.patient_phone and settings.sns_enabled:
            try:
                result = await self.notification_service.send_welcome_sms(
                    phone_number=referral.patient_phone,
                    first_name=referral.patient_first_name,
                )
                
                if onboarding:
                    onboarding.welcome_sms_sent = True
                    onboarding.welcome_sms_sent_at = datetime.utcnow()
                
                self._log_notification(
                    patient_uuid=referral.patient_uuid,
                    referral_uuid=referral.uuid,
                    notification_type="welcome",
                    channel="sms",
                    recipient=referral.patient_phone,
                    status="sent",
                    message_id=result.get("message_id"),
                )
                
            except Exception as e:
                logger.error(f"Failed to send welcome SMS: {e}")
                self._log_notification(
                    patient_uuid=referral.patient_uuid,
                    referral_uuid=referral.uuid,
                    notification_type="welcome",
                    channel="sms",
                    recipient=referral.patient_phone,
                    status="failed",
                    status_message=str(e),
                )
    
    def _log_notification(
        self,
        patient_uuid: UUID,
        referral_uuid: UUID,
        notification_type: str,
        channel: str,
        recipient: str,
        status: str,
        message_id: Optional[str] = None,
        status_message: Optional[str] = None,
    ) -> None:
        """Log notification for audit trail."""
        log_entry = OnboardingNotificationLog(
            patient_uuid=patient_uuid,
            referral_uuid=referral_uuid,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            status=status,
            aws_message_id=message_id,
            status_message=status_message,
        )
        self.patient_db.add(log_entry)
    
    # =========================================================================
    # ONBOARDING FLOW MANAGEMENT
    # =========================================================================
    
    def get_onboarding_status(
        self,
        patient_uuid: str,
    ) -> Dict[str, Any]:
        """
        Get current onboarding status for a patient.
        
        Args:
            patient_uuid: Patient UUID
            
        Returns:
            Dict with current step and completion status
        """
        status = self.patient_db.query(PatientOnboardingStatus).filter(
            PatientOnboardingStatus.patient_uuid == patient_uuid
        ).first()
        
        if not status:
            return {
                "is_onboarded": True,  # No record means legacy patient
                "current_step": None,
            }
        
        return {
            "is_onboarded": status.is_fully_onboarded,
            "current_step": status.current_step,
            "steps": {
                "password_reset": status.password_reset_completed,
                "acknowledgement": status.acknowledgement_completed,
                "terms_privacy": status.terms_accepted and status.privacy_accepted,
                "reminder_setup": status.reminder_preference_set,
            },
            "first_login_at": status.first_login_at.isoformat() if status.first_login_at else None,
            "onboarding_completed_at": status.onboarding_completed_at.isoformat() if status.onboarding_completed_at else None,
        }
    
    def complete_password_reset(
        self,
        patient_uuid: str,
    ) -> Dict[str, Any]:
        """Mark password reset step as complete."""
        status = self._get_or_create_onboarding_status(patient_uuid)
        
        status.password_reset_completed = True
        status.password_reset_at = datetime.utcnow()
        status.current_step = OnboardingStep.ACKNOWLEDGEMENT.value
        
        if not status.first_login_at:
            status.first_login_at = datetime.utcnow()
        
        self.patient_db.commit()
        
        return self.get_onboarding_status(patient_uuid)
    
    def complete_acknowledgement(
        self,
        patient_uuid: str,
        acknowledgement_text: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark acknowledgement step as complete."""
        status = self._get_or_create_onboarding_status(patient_uuid)
        
        status.acknowledgement_completed = True
        status.acknowledgement_text = acknowledgement_text
        status.acknowledgement_at = datetime.utcnow()
        status.acknowledgement_ip = ip_address
        status.current_step = OnboardingStep.TERMS_PRIVACY.value
        
        self.patient_db.commit()
        
        return self.get_onboarding_status(patient_uuid)
    
    def complete_terms_privacy(
        self,
        patient_uuid: str,
        terms_accepted: bool,
        privacy_accepted: bool,
        hipaa_acknowledged: bool = True,
    ) -> Dict[str, Any]:
        """Mark terms and privacy step as complete."""
        if not terms_accepted or not privacy_accepted:
            raise ValidationError(
                message="Both terms and privacy policy must be accepted",
                field="acceptance",
            )
        
        status = self._get_or_create_onboarding_status(patient_uuid)
        
        status.terms_accepted = True
        status.terms_version = settings.terms_version
        status.terms_accepted_at = datetime.utcnow()
        
        status.privacy_accepted = True
        status.privacy_version = settings.privacy_version
        status.privacy_accepted_at = datetime.utcnow()
        
        status.hipaa_acknowledged = hipaa_acknowledged
        status.hipaa_version = settings.hipaa_version
        status.hipaa_acknowledged_at = datetime.utcnow()
        
        status.current_step = OnboardingStep.REMINDER_SETUP.value
        
        # Also update patient configurations
        config = self.patient_db.query(PatientConfigurations).filter(
            PatientConfigurations.uuid == patient_uuid
        ).first()
        
        if config:
            config.acknowledgement_done = True
            config.agreed_conditions = True
        
        self.patient_db.commit()
        
        return self.get_onboarding_status(patient_uuid)
    
    def complete_reminder_setup(
        self,
        patient_uuid: str,
        channel: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        reminder_time: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete reminder setup and finalize onboarding."""
        status = self._get_or_create_onboarding_status(patient_uuid)
        
        status.reminder_preference_set = True
        status.reminder_channel = channel
        status.reminder_email = email
        status.reminder_phone = phone
        status.reminder_time = reminder_time
        status.reminder_timezone = timezone
        status.reminder_preference_at = datetime.utcnow()
        
        # Mark onboarding as complete
        status.current_step = OnboardingStep.COMPLETED.value
        status.is_fully_onboarded = True
        status.onboarding_completed_at = datetime.utcnow()
        
        # Update patient configuration
        config = self.patient_db.query(PatientConfigurations).filter(
            PatientConfigurations.uuid == patient_uuid
        ).first()
        
        if config:
            config.reminder_method = channel
            if reminder_time:
                from datetime import time as time_type
                try:
                    hours, minutes = map(int, reminder_time.split(":"))
                    config.reminder_time = time_type(hours, minutes)
                except ValueError:
                    pass
        
        # Update referral status
        if status.referral_uuid:
            referral = self.patient_db.query(PatientReferral).filter(
                PatientReferral.uuid == status.referral_uuid
            ).first()
            if referral:
                referral.status = ReferralStatus.COMPLETED.value
        
        self.patient_db.commit()
        
        logger.info(f"Patient onboarding completed: {patient_uuid}")
        
        return self.get_onboarding_status(patient_uuid)
    
    def _get_or_create_onboarding_status(
        self,
        patient_uuid: str,
    ) -> PatientOnboardingStatus:
        """Get or create onboarding status record."""
        status = self.patient_db.query(PatientOnboardingStatus).filter(
            PatientOnboardingStatus.patient_uuid == patient_uuid
        ).first()
        
        if not status:
            status = PatientOnboardingStatus(
                patient_uuid=patient_uuid,
                current_step=OnboardingStep.PASSWORD_RESET.value,
            )
            self.patient_db.add(status)
            self.patient_db.flush()
        
        return status
    
    # =========================================================================
    # MANUAL REVIEW
    # =========================================================================
    
    def get_fields_needing_review(
        self,
        fax_id: str,
    ) -> List[Dict]:
        """
        Get all fields that need manual review for a fax.
        
        Args:
            fax_id: Fax ingestion log UUID
            
        Returns:
            List of fields with their values and confidence scores
        """
        fields = self.patient_db.query(OcrFieldConfidence).filter(
            OcrFieldConfidence.fax_id == fax_id,
            OcrFieldConfidence.accepted == False,
        ).all()
        
        return [
            {
                "id": field.id,
                "field_name": field.field_name,
                "field_category": field.field_category,
                "extracted_value": field.extracted_value,
                "confidence_score": float(field.confidence_score),
                "confidence_threshold": float(field.confidence_threshold),
                "status": field.status,
            }
            for field in fields
        ]
    
    def approve_field(
        self,
        field_id: int,
        approved_by: str,
    ) -> Dict:
        """
        Approve an extracted field value.
        
        Args:
            field_id: OcrFieldConfidence record ID
            approved_by: User who approved
            
        Returns:
            Updated field data
        """
        field = self.patient_db.query(OcrFieldConfidence).filter(
            OcrFieldConfidence.id == field_id
        ).first()
        
        if not field:
            raise NotFoundError(
                message=f"Field {field_id} not found",
                resource_type="OcrFieldConfidence",
                resource_id=str(field_id),
            )
        
        field.status = OcrFieldStatus.MANUALLY_VERIFIED.value
        field.accepted = True
        field.reviewed_at = datetime.utcnow()
        field.reviewed_by = approved_by
        
        self.patient_db.commit()
        
        # Check if all fields are now approved
        self._check_review_complete(field.fax_id)
        
        return {
            "id": field.id,
            "field_name": field.field_name,
            "status": field.status,
            "accepted": field.accepted,
        }
    
    def correct_field(
        self,
        field_id: int,
        corrected_value: str,
        corrected_by: str,
        reason: Optional[str] = None,
    ) -> Dict:
        """
        Correct an extracted field value.
        
        Args:
            field_id: OcrFieldConfidence record ID
            corrected_value: The correct value
            corrected_by: User who corrected
            reason: Reason for correction (optional)
            
        Returns:
            Updated field data
        """
        field = self.patient_db.query(OcrFieldConfidence).filter(
            OcrFieldConfidence.id == field_id
        ).first()
        
        if not field:
            raise NotFoundError(
                message=f"Field {field_id} not found",
                resource_type="OcrFieldConfidence",
                resource_id=str(field_id),
            )
        
        field.status = OcrFieldStatus.CORRECTED.value
        field.accepted = True
        field.corrected_value = corrected_value
        field.normalized_value = corrected_value
        field.correction_reason = reason
        field.reviewed_at = datetime.utcnow()
        field.reviewed_by = corrected_by
        
        self.patient_db.commit()
        
        # Check if all fields are now approved
        self._check_review_complete(field.fax_id)
        
        return {
            "id": field.id,
            "field_name": field.field_name,
            "original_value": field.extracted_value,
            "corrected_value": field.corrected_value,
            "status": field.status,
            "accepted": field.accepted,
        }
    
    def _check_review_complete(self, fax_id: UUID) -> None:
        """Check if all fields for a fax have been reviewed."""
        pending_fields = self.patient_db.query(OcrFieldConfidence).filter(
            OcrFieldConfidence.fax_id == fax_id,
            OcrFieldConfidence.accepted == False,
        ).count()
        
        if pending_fields == 0:
            # All fields reviewed, update fax log
            fax_log = self.patient_db.query(FaxIngestionLog).filter(
                FaxIngestionLog.fax_id == fax_id
            ).first()
            
            if fax_log and fax_log.ocr_status == FaxProcessingStatus.REVIEW_NEEDED.value:
                fax_log.ocr_status = FaxProcessingStatus.APPROVED.value
                fax_log.reviewed_at = datetime.utcnow()
                
                logger.info(f"All fields reviewed for fax: {fax_id}")
    
    # =========================================================================
    # MANUAL REFERRAL ENTRY
    # =========================================================================
    
    async def create_manual_referral(
        self,
        patient_data: Dict[str, Any],
        physician_data: Optional[Dict[str, Any]] = None,
        treatment_data: Optional[Dict[str, Any]] = None,
        send_welcome: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a referral manually (for cases where OCR fails or for testing).
        
        Args:
            patient_data: Patient demographics
            physician_data: Physician and clinic info (optional)
            treatment_data: Treatment/chemo info (optional)
            send_welcome: Whether to send welcome notifications
            
        Returns:
            Dict with referral and patient info
        """
        logger.info(f"Creating manual referral for: {patient_data.get('email')}")
        
        # Create referral
        referral = PatientReferral(
            status=ReferralStatus.PARSED.value,
            patient_first_name=patient_data.get("first_name"),
            patient_last_name=patient_data.get("last_name"),
            patient_email=patient_data.get("email"),
            patient_phone=patient_data.get("phone"),
            patient_dob=patient_data.get("dob"),
            patient_sex=patient_data.get("sex"),
            patient_mrn=patient_data.get("mrn"),
        )
        
        if physician_data:
            referral.attending_physician_name = physician_data.get("name")
            referral.clinic_name = physician_data.get("clinic")
        
        if treatment_data:
            referral.cancer_type = treatment_data.get("cancer_type")
            referral.cancer_staging = treatment_data.get("staging")
            referral.chemo_plan_name = treatment_data.get("plan_name")
            referral.chemo_start_date = treatment_data.get("start_date")
            referral.chemo_end_date = treatment_data.get("end_date")
            referral.line_of_treatment = treatment_data.get("line_of_treatment")
        
        self.patient_db.add(referral)
        self.patient_db.flush()
        
        # Create provider if provided
        provider = None
        if physician_data and physician_data.get("name"):
            provider = Provider(
                full_name=physician_data["name"],
                clinic_name=physician_data.get("clinic"),
            )
            self.patient_db.add(provider)
            self.patient_db.flush()
        
        # Create patient account
        patient_result = await self._create_patient_from_referral(referral)
        patient_uuid = patient_result["uuid"]
        
        # Create oncology profile if treatment data provided
        if treatment_data:
            profile = OncologyProfile(
                patient_id=patient_uuid,
                provider_id=provider.provider_id if provider else None,
                referral_uuid=referral.uuid,
                cancer_type=treatment_data.get("cancer_type"),
                cancer_stage=treatment_data.get("staging"),
                line_of_treatment=treatment_data.get("line_of_treatment"),
                chemo_plan_name=treatment_data.get("plan_name"),
                chemo_start_date=treatment_data.get("start_date"),
                chemo_end_date=treatment_data.get("end_date"),
            )
            self.patient_db.add(profile)
        
        # Send welcome if requested
        if send_welcome:
            await self._send_welcome_notifications(referral)
            referral.status = ReferralStatus.WELCOME_SENT.value
        
        self.patient_db.commit()
        
        return {
            "success": True,
            "referral_uuid": str(referral.uuid),
            "patient_uuid": str(patient_uuid),
            "status": referral.status,
        }
