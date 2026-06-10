"""
Education Service - Post-Conversation Education Delivery.

This service handles the complete education delivery flow:
1. Triggered when symptom checker session completes
2. Fetches education mappings for each symptom
3. Validates documents are active + approved
4. Assembles inline education blocks
5. Appends mandatory disclaimer
6. Returns payload to chat UI

Design Principles:
- No AI/LLM generation
- All content is clinician-approved
- Inline text copied verbatim from source docs
- Mandatory disclaimer on every response
- Care Team Handout always included
- Full audit trail

AWS Integration:
- S3 for document storage (KMS encrypted)
- Pre-signed URLs for secure access
- RDS for metadata
"""

import boto3
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from botocore.exceptions import ClientError

from core.config import settings
from core.logging import get_logger
from core.exceptions import NotFoundError, ExternalServiceError

from db.models.education import (
    Symptom,
    SymptomSession,
    RuleEvaluation,
    EducationDocument,
    Disclaimer,
    CareTeamHandout,
    PatientSummary,
    MedicationTried,
    EducationDeliveryLog,
    EducationAccessLog,
    SessionStatus,
    DocumentStatus,
    TriageSeverity,
)

logger = get_logger(__name__)


# =============================================================================
# SUMMARY TEMPLATES (Deterministic, No AI)
# =============================================================================

SUMMARY_TEMPLATES = {
    "default": (
        "You reported {symptom_list} with {severity_list} severity. "
        "{medication_sentence}"
        "{escalation_sentence}"
    ),
    "single_symptom": (
        "You reported {symptom_name} ({severity}). "
        "{medication_sentence}"
        "{escalation_sentence}"
    ),
    "no_symptoms": (
        "You indicated you are not experiencing any symptoms today. "
        "Continue to monitor how you feel and report any changes."
    ),
}

ESCALATION_SENTENCES = {
    True: "Based on your responses, we recommend contacting your care team promptly.",
    False: "No urgent symptoms were detected. Continue monitoring and follow your care plan.",
}


class EducationService:
    """
    Service for education content delivery.
    
    Responsibilities:
    - Fetch and validate education documents
    - Generate pre-signed S3 URLs
    - Assemble education payload for frontend
    - Track delivery for audit
    - Generate deterministic patient summaries
    """
    
    # Pre-signed URL expiration (minutes)
    URL_EXPIRY_MINUTES = 30
    
    def __init__(
        self,
        db: Session,
        s3_client: Optional[Any] = None,
    ):
        """
        Initialize education service.
        
        Args:
            db: Database session
            s3_client: AWS S3 client (optional)
        """
        self.db = db
        self._s3_client = s3_client
        self.s3_bucket = settings.s3_education_bucket
    
    @property
    def s3_client(self):
        """Get or create S3 client with Signature Version 4."""
        if self._s3_client is None:
            from botocore.config import Config
            # Use signature v4 for modern S3 regions
            s3_config = Config(signature_version='s3v4')
            self._s3_client = boto3.client(
                "s3",
                region_name=settings.aws_region,
                config=s3_config,
            )
        return self._s3_client
    
    # =========================================================================
    # POST-CONVERSATION EDUCATION DELIVERY
    # =========================================================================
    
    async def deliver_post_session_education(
        self,
        session_id: UUID,
        symptom_codes: List[str],
        severity_levels: Dict[str, str],
        escalation: bool = False,
    ) -> Dict[str, Any]:
        """
        Main entry point: Deliver education after symptom session completes.
        
        This is triggered when: Rule Engine Status = COMPLETED
        
        Args:
            session_id: Symptom session UUID
            symptom_codes: List of symptom codes (e.g., ["BLEED-103", "NAUSEA-101"])
            severity_levels: Dict of symptom code -> severity
            escalation: Whether escalation was triggered
            
        Returns:
            Education payload for frontend rendering
        """
        logger.info(f"Delivering education for session: {session_id}")
        
        # Step 1: Validate session exists
        session = self.db.query(SymptomSession).filter(
            SymptomSession.id == session_id
        ).first()
        
        if not session:
            raise NotFoundError(
                message=f"Session {session_id} not found",
                resource_type="SymptomSession",
                resource_id=str(session_id),
            )
        
        # Step 2: Fetch education documents for each symptom
        education_blocks = []
        for symptom_code in symptom_codes:
            block = await self._get_education_block(
                symptom_code=symptom_code,
                severity=severity_levels.get(symptom_code, "mild"),
            )
            if block:
                education_blocks.append(block)
        
        # Step 3: Always include Care Team Handout
        care_team_block = await self._get_care_team_handout()
        if care_team_block:
            education_blocks.append(care_team_block)
        
        # Step 4: Get mandatory disclaimer
        disclaimer = self._get_mandatory_disclaimer()
        
        # Step 5: Log delivery for audit
        self._log_education_delivery(
            session_id=session_id,
            patient_id=session.patient_id,
            education_blocks=education_blocks,
            disclaimer_id=disclaimer["id"],
        )
        
        # Step 6: Update session status
        session.education_delivered = True
        session.status = SessionStatus.COMPLETED.value
        session.completed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Education delivered: {len(education_blocks)} blocks")
        
        return {
            "session_id": str(session_id),
            "educationBlocks": education_blocks,
            "disclaimer": disclaimer,
            "escalation": escalation,
            "delivered_at": datetime.utcnow().isoformat(),
        }
    
    async def _get_education_block(
        self,
        symptom_code: str,
        severity: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get education block for a specific symptom.
        
        Fetches active, approved documents and generates pre-signed URLs.
        """
        # Query active documents for this symptom
        documents = self.db.query(EducationDocument).filter(
            and_(
                EducationDocument.symptom_code == symptom_code,
                EducationDocument.status == DocumentStatus.ACTIVE.value,
            )
        ).order_by(EducationDocument.priority.desc()).all()
        
        if not documents:
            logger.warning(f"No education documents for symptom: {symptom_code}")
            return None
        
        # Get symptom name
        symptom = self.db.query(Symptom).filter(
            Symptom.code == symptom_code
        ).first()
        
        symptom_name = symptom.name if symptom else symptom_code
        
        # Build resource links with pre-signed URLs
        resource_links = []
        inline_text = None
        
        for doc in documents:
            # Use first document's inline text
            if inline_text is None:
                inline_text = doc.inline_text
            
            # Generate pre-signed URL for PDF
            try:
                presigned_url = self._generate_presigned_url(doc.s3_pdf_path)
                resource_links.append({
                    "title": doc.title,
                    "url": presigned_url,
                    "document_id": str(doc.id),
                    "type": "pdf",
                })
            except Exception as e:
                logger.error(f"Failed to generate URL for {doc.s3_pdf_path}: {e}")
        
        return {
            "symptom": symptom_name,
            "symptom_code": symptom_code,
            "severity": severity,
            "inlineText": inline_text,
            "inlineTextId": f"EDU-{symptom_code}-01",
            "resourceLinks": resource_links,
        }
    
    async def _get_care_team_handout(self) -> Optional[Dict[str, Any]]:
        """
        Get Care Team Handout (always included).
        
        This is a special document that's attached to every education response.
        """
        handout = self.db.query(CareTeamHandout).filter(
            CareTeamHandout.is_current == True
        ).first()
        
        if not handout:
            logger.warning("No current Care Team Handout found")
            return None
        
        try:
            presigned_url = self._generate_presigned_url(handout.s3_pdf_path)
            
            return {
                "symptom": "Care Team Information",
                "symptom_code": "CARE-TEAM",
                "inlineText": handout.inline_summary,
                "inlineTextId": f"CARE-TEAM-v{handout.version}",
                "resourceLinks": [
                    {
                        "title": handout.title,
                        "url": presigned_url,
                        "document_id": str(handout.id),
                        "type": "pdf",
                        "label": "Read more from your care team",
                    }
                ],
                "is_care_team_handout": True,
            }
        except Exception as e:
            logger.error(f"Failed to get Care Team Handout: {e}")
            return None
    
    def _get_mandatory_disclaimer(self) -> Dict[str, str]:
        """
        Get mandatory disclaimer (always shown).
        
        Returns cached or database disclaimer.
        """
        disclaimer = self.db.query(Disclaimer).filter(
            Disclaimer.active == True
        ).first()
        
        if disclaimer:
            return {
                "id": disclaimer.id,
                "text": disclaimer.text,
            }
        
        # Fallback to hardcoded (should never happen in production)
        return {
            "id": "STD-DISCLAIMER-001",
            "text": (
                "This information is for education only and does not replace medical advice. "
                "Always follow instructions from your oncology care team."
            ),
        }
    
    def _generate_presigned_url(
        self,
        s3_key: str,
        expiry_minutes: int = None,
    ) -> str:
        """
        Generate URL for education document access.
        
        In development mode (without S3 bucket): Returns local static file URL
        In production/staging (with S3 bucket): Returns pre-signed S3 URL (time-limited, default 30 minutes)
        """
        # Use S3 if bucket is configured (staging/production), otherwise use local static files
        # This allows LOCAL_DEV_MODE=true for demo login while still using S3 for education
        use_local = (settings.is_development or settings.local_dev_mode) and not self.s3_bucket
        
        if use_local:
            # Return local static file URL
            # Files are served via FastAPI StaticFiles mount at /static/
            local_url = f"/static/education/{s3_key}"
            logger.debug(f"Using local static URL: {local_url}")
            return local_url
        
        # Production: Generate S3 pre-signed URL
        expiry_minutes = expiry_minutes or self.URL_EXPIRY_MINUTES
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.s3_bucket,
                    "Key": s3_key,
                },
                ExpiresIn=expiry_minutes * 60,
            )
            return url
        except ClientError as e:
            logger.error(f"S3 presigned URL error: {e}")
            raise ExternalServiceError(
                message="Failed to generate document URL",
                service_name="AWS S3",
            )
    
    def _log_education_delivery(
        self,
        session_id: UUID,
        patient_id: UUID,
        education_blocks: List[Dict],
        disclaimer_id: str,
    ) -> None:
        """Log education delivery for audit trail."""
        for block in education_blocks:
            for link in block.get("resourceLinks", []):
                if "document_id" in link:
                    log_entry = EducationDeliveryLog(
                        session_id=session_id,
                        education_document_id=UUID(link["document_id"]),
                        patient_id=patient_id,
                        disclaimer_id=disclaimer_id,
                        care_team_handout_included=block.get("is_care_team_handout", False),
                    )
                    self.db.add(log_entry)
    
    # =========================================================================
    # PATIENT SUMMARY GENERATION (Deterministic Templates)
    # =========================================================================
    
    def generate_patient_summary(
        self,
        session_id: UUID,
        patient_id: UUID,
        symptoms: List[Dict[str, str]],  # [{code, name, severity}]
        medications_tried: List[Dict[str, str]],  # [{name, effectiveness}]
        escalation: bool,
    ) -> PatientSummary:
        """
        Generate deterministic patient summary from template.
        
        NO AI/LLM generation - pure template substitution.
        
        Template:
            "You reported {{symptom_list}} with {{severity_list}} severity.
            You tried {{medications_tried}} with {{effectiveness}}.
            {{escalation_sentence}}"
        
        Args:
            session_id: Session UUID
            patient_id: Patient UUID
            symptoms: List of symptom dicts with code, name, severity
            medications_tried: List of medication dicts
            escalation: Whether escalation was triggered
            
        Returns:
            Created PatientSummary
        """
        logger.info(f"Generating summary for session: {session_id}")
        
        # Build symptom list string
        if not symptoms:
            summary_text = SUMMARY_TEMPLATES["no_symptoms"]
        elif len(symptoms) == 1:
            s = symptoms[0]
            medication_sentence = self._build_medication_sentence(medications_tried)
            escalation_sentence = ESCALATION_SENTENCES[escalation]
            
            summary_text = SUMMARY_TEMPLATES["single_symptom"].format(
                symptom_name=s["name"],
                severity=s["severity"],
                medication_sentence=medication_sentence,
                escalation_sentence=escalation_sentence,
            )
        else:
            symptom_list = ", ".join(s["name"] for s in symptoms)
            severity_list = ", ".join(
                f"{s['name']} ({s['severity']})" for s in symptoms
            )
            medication_sentence = self._build_medication_sentence(medications_tried)
            escalation_sentence = ESCALATION_SENTENCES[escalation]
            
            summary_text = SUMMARY_TEMPLATES["default"].format(
                symptom_list=symptom_list,
                severity_list=severity_list,
                medication_sentence=medication_sentence,
                escalation_sentence=escalation_sentence,
            )
        
        # Create immutable summary
        summary = PatientSummary(
            session_id=session_id,
            patient_id=patient_id,
            summary_text=summary_text.strip(),
            escalation=escalation,
            locked=True,  # Always locked
            template_id="default",
        )
        
        self.db.add(summary)
        self.db.commit()
        
        logger.info(f"Summary generated: {summary.id}")
        
        return summary
    
    def _build_medication_sentence(
        self,
        medications_tried: List[Dict[str, str]],
    ) -> str:
        """Build medication sentence for summary template."""
        if not medications_tried:
            return ""
        
        med_parts = []
        for med in medications_tried:
            name = med.get("name", "medication")
            effectiveness = med.get("effectiveness", "unknown")
            
            if effectiveness == "helped":
                med_parts.append(f"{name} (helped)")
            elif effectiveness == "partial":
                med_parts.append(f"{name} (partial relief)")
            else:
                med_parts.append(f"{name} (no relief)")
        
        if len(med_parts) == 1:
            return f"You tried {med_parts[0]}. "
        else:
            return f"You tried {', '.join(med_parts[:-1])} and {med_parts[-1]}. "
    
    def add_patient_note(
        self,
        summary_id: UUID,
        patient_note: str,
    ) -> PatientSummary:
        """
        Add patient's optional note to summary.
        
        Max 300 characters. Does not modify system-generated text.
        """
        summary = self.db.query(PatientSummary).filter(
            PatientSummary.id == summary_id
        ).first()
        
        if not summary:
            raise NotFoundError(
                message=f"Summary {summary_id} not found",
                resource_type="PatientSummary",
                resource_id=str(summary_id),
            )
        
        # Enforce max length
        if len(patient_note) > 300:
            patient_note = patient_note[:300]
        
        summary.patient_note = patient_note
        self.db.commit()
        
        return summary
    
    # =========================================================================
    # EDUCATION TAB (Read-Only Library)
    # =========================================================================
    
    def get_education_tab_content(
        self,
        patient_id: UUID,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get education tab content for patient.
        
        Default view logic:
        1. Fetch last 7 days of symptoms
        2. Rank documents by relevance
        3. Render "My Current Symptoms" first
        
        Args:
            patient_id: Patient UUID
            limit: Max documents to return
            
        Returns:
            Organized education content
        """
        logger.info(f"Fetching education tab for patient: {patient_id}")
        
        # Get recent symptoms (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_sessions = self.db.query(SymptomSession).filter(
            and_(
                SymptomSession.patient_id == patient_id,
                SymptomSession.completed_at >= seven_days_ago,
                SymptomSession.status == SessionStatus.COMPLETED.value,
            )
        ).all()
        
        # Extract symptom codes
        active_symptoms = set()
        for session in recent_sessions:
            if session.selected_symptoms:
                active_symptoms.update(session.selected_symptoms)
        
        # Section 1: My Current Symptoms
        current_symptom_docs = []
        if active_symptoms:
            docs = self.db.query(EducationDocument).filter(
                and_(
                    EducationDocument.symptom_code.in_(active_symptoms),
                    EducationDocument.status == DocumentStatus.ACTIVE.value,
                )
            ).order_by(EducationDocument.priority.desc()).limit(limit).all()
            
            for doc in docs:
                current_symptom_docs.append(self._format_education_doc(doc))
        
        # Section 2: Common Chemotherapy Symptoms
        common_symptoms = ["NAUSEA-101", "FATIGUE-101", "PAIN-101", "APPETITE-101"]
        common_docs = self.db.query(EducationDocument).filter(
            and_(
                EducationDocument.symptom_code.in_(common_symptoms),
                EducationDocument.status == DocumentStatus.ACTIVE.value,
            )
        ).order_by(EducationDocument.priority.desc()).limit(10).all()
        
        common_symptom_docs = [self._format_education_doc(doc) for doc in common_docs]
        
        # Section 3: Care Team Handouts
        handouts = self.db.query(CareTeamHandout).filter(
            CareTeamHandout.is_current == True
        ).all()
        
        care_team_docs = [self._format_handout(h) for h in handouts]
        
        return {
            "my_current_symptoms": current_symptom_docs,
            "common_symptoms": common_symptom_docs,
            "care_team_handouts": care_team_docs,
            "active_symptom_codes": list(active_symptoms),
            "last_updated": datetime.utcnow().isoformat(),
        }
    
    def _format_education_doc(self, doc: EducationDocument) -> Dict[str, Any]:
        """Format education document for API response."""
        try:
            pdf_url = self._generate_presigned_url(doc.s3_pdf_path)
        except Exception:
            pdf_url = None
        
        return {
            "id": str(doc.id),
            "symptom_code": doc.symptom_code,
            "title": doc.title,
            "inline_text": doc.inline_text,
            "pdf_url": pdf_url,
            "version": doc.version,
            "approved_date": doc.approved_date.isoformat() if doc.approved_date else None,
        }
    
    def _format_handout(self, handout: CareTeamHandout) -> Dict[str, Any]:
        """Format care team handout for API response."""
        try:
            pdf_url = self._generate_presigned_url(handout.s3_pdf_path)
        except Exception:
            pdf_url = None
        
        return {
            "id": str(handout.id),
            "title": handout.title,
            "inline_summary": handout.inline_summary,
            "pdf_url": pdf_url,
            "version": handout.version,
        }
    
    def search_education(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Simple search for education documents.
        
        Implementation: SQL ILIKE search (no embeddings, no NLP).
        """
        search_term = f"%{query}%"
        
        docs = self.db.query(EducationDocument).filter(
            and_(
                EducationDocument.status == DocumentStatus.ACTIVE.value,
                (
                    EducationDocument.title.ilike(search_term) |
                    EducationDocument.inline_text.ilike(search_term)
                ),
            )
        ).limit(limit).all()
        
        return [self._format_education_doc(doc) for doc in docs]
    
    def log_education_access(
        self,
        patient_id: UUID,
        document_id: UUID,
        access_type: str = "view",
        source: str = "education_tab",
    ) -> None:
        """Log education tab access for analytics."""
        log_entry = EducationAccessLog(
            patient_id=patient_id,
            education_document_id=document_id,
            access_type=access_type,
            source=source,
        )
        self.db.add(log_entry)
        self.db.commit()
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def create_symptom_session(
        self,
        patient_id: UUID,
        conversation_uuid: Optional[UUID] = None,
    ) -> SymptomSession:
        """Create a new symptom session."""
        session = SymptomSession(
            patient_id=patient_id,
            conversation_uuid=conversation_uuid,
            status=SessionStatus.IN_PROGRESS.value,
        )
        self.db.add(session)
        self.db.commit()
        
        logger.info(f"Created symptom session: {session.id}")
        return session
    
    def record_rule_evaluation(
        self,
        session_id: UUID,
        symptom_code: str,
        rule_id: str,
        condition_met: bool,
        severity: Optional[str] = None,
        escalation: bool = False,
        trigger_answers: Optional[Dict] = None,
        triage_message: Optional[str] = None,
    ) -> RuleEvaluation:
        """Record a rule evaluation for audit."""
        evaluation = RuleEvaluation(
            session_id=session_id,
            symptom_code=symptom_code,
            rule_id=rule_id,
            condition_met=condition_met,
            severity=severity,
            escalation=escalation,
            trigger_answers=trigger_answers,
            triage_message=triage_message,
        )
        self.db.add(evaluation)
        self.db.commit()
        
        return evaluation
    
    def record_medication_tried(
        self,
        session_id: UUID,
        medication_name: str,
        effectiveness: str = "none",
        category: Optional[str] = None,
    ) -> MedicationTried:
        """Record a medication tried during session."""
        med = MedicationTried(
            session_id=session_id,
            medication_name=medication_name,
            effectiveness=effectiveness,
            medication_category=category,
        )
        self.db.add(med)
        self.db.commit()
        
        return med

