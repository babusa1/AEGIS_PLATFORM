"""
Scribe Agent

The Scribe Agent generates high-fidelity clinical artifacts:
- SOAP Notes: Progress notes in specific SOAP format
- Referral Letters: Professional referral letters
- Prior Authorization: Prior-auth requests
- Order Drafting: Pre-populates CPOE fields
- Patient Translation: Multilingual instructions at 5th-grade reading level

This wraps ActionAgent with Scribe-specific document generation methods.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

from aegis.agents.action import ActionAgent
from aegis.cowork.models import CoworkArtifact, ArtifactType
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class ScribeAgent:
    """
    Scribe Agent - Intervention Architect
    
    The Scribe generates high-fidelity clinical artifacts.
    
    Features:
    1. EHR Post-Back: Pre-drafts Progress Notes in specific "SOAP" format
    2. Order Drafting: Pre-populates CPOE (Computerized Physician Order Entry) fields
    3. Multilingual Translation: Translates clinical discharge plans into patient's native language
    
    This wraps ActionAgent with Scribe-specific document generation methods.
    """
    
    def __init__(
        self,
        tenant_id: str,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize Scribe Agent.
        
        Args:
            tenant_id: Tenant ID
            llm_client: LLM client
        """
        self.tenant_id = tenant_id
        
        # Wrap ActionAgent
        self.action_agent = ActionAgent(
            tenant_id=tenant_id,
            llm_client=llm_client,
        )
        
        logger.info("ScribeAgent initialized", tenant_id=tenant_id)
    
    # =========================================================================
    # SOAP Note Generation
    # =========================================================================
    
    async def generate_soap_note(
        self,
        patient_id: str,
        encounter_id: Optional[str] = None,
        chief_complaint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CoworkArtifact:
        """
        Generate SOAP note (Subjective, Objective, Assessment, Plan).
        
        Args:
            patient_id: Patient ID
            encounter_id: Optional encounter ID
            chief_complaint: Chief complaint
            context: Optional clinical context
            
        Returns:
            CoworkArtifact with SOAP note
        """
        logger.info(
            "Generating SOAP note",
            patient_id=patient_id,
            encounter_id=encounter_id,
        )
        
        # Gather patient context
        if not context:
            context = await self._gather_patient_context(patient_id)
        
        # Generate SOAP note using LLM
        soap_prompt = f"""Generate a professional SOAP note for this patient encounter.

PATIENT INFORMATION:
- Patient ID: {patient_id}
- Encounter ID: {encounter_id or 'N/A'}
- Chief Complaint: {chief_complaint or 'Not specified'}

CLINICAL CONTEXT:
{self._format_context_for_soap(context)}

Generate a complete SOAP note with:
1. SUBJECTIVE: Patient's history, symptoms, concerns
2. OBJECTIVE: Physical exam findings, vital signs, lab results
3. ASSESSMENT: Clinical assessment, diagnoses, differential diagnoses
4. PLAN: Treatment plan, medications, follow-up, patient education

Use professional medical terminology and format.
"""
        
        soap_content = await self.action_agent.llm.generate(
            prompt=soap_prompt,
            system_prompt="You are a clinical documentation specialist. Generate professional SOAP notes.",
        )
        
        # Create artifact
        artifact = CoworkArtifact(
            type=ArtifactType.SOAP_NOTE,
            title=f"SOAP Note - {patient_id}",
            content=soap_content,
            created_by="scribe_agent",
            metadata={
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "chief_complaint": chief_complaint,
            },
        )
        
        return artifact
    
    # =========================================================================
    # Referral Letter Generation
    # =========================================================================
    
    async def generate_referral_letter(
        self,
        patient_id: str,
        referring_provider: str,
        receiving_provider: str,
        specialty: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> CoworkArtifact:
        """
        Generate referral letter.
        
        Args:
            patient_id: Patient ID
            referring_provider: Referring provider name
            receiving_provider: Receiving provider name
            specialty: Specialty (e.g., "Cardiology", "Nephrology")
            reason: Reason for referral
            context: Optional clinical context
            
        Returns:
            CoworkArtifact with referral letter
        """
        logger.info(
            "Generating referral letter",
            patient_id=patient_id,
            specialty=specialty,
        )
        
        # Gather patient context
        if not context:
            context = await self._gather_patient_context(patient_id)
        
        # Generate referral letter
        referral_prompt = f"""Generate a professional referral letter.

REFERRAL INFORMATION:
- Patient ID: {patient_id}
- Referring Provider: {referring_provider}
- Receiving Provider: {receiving_provider}
- Specialty: {specialty}
- Reason for Referral: {reason}

CLINICAL CONTEXT:
{self._format_context_for_referral(context)}

Generate a complete referral letter with:
1. Patient identification and demographics
2. Chief complaint and reason for referral
3. Relevant clinical history
4. Current medications and allergies
5. Recent lab results and imaging
6. Specific questions or concerns for the specialist
7. Request for consultation and follow-up

Use professional medical letter format.
"""
        
        referral_content = await self.action_agent.llm.generate(
            prompt=referral_prompt,
            system_prompt="You are a clinical documentation specialist. Generate professional referral letters.",
        )
        
        # Create artifact
        artifact = CoworkArtifact(
            type=ArtifactType.REFERRAL_LETTER,
            title=f"Referral to {specialty} - {patient_id}",
            content=referral_content,
            created_by="scribe_agent",
            metadata={
                "patient_id": patient_id,
                "referring_provider": referring_provider,
                "receiving_provider": receiving_provider,
                "specialty": specialty,
                "reason": reason,
            },
        )
        
        return artifact
    
    # =========================================================================
    # Prior Authorization Generation
    # =========================================================================
    
    async def generate_prior_auth(
        self,
        patient_id: str,
        service: str,
        diagnosis: str,
        payer: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> CoworkArtifact:
        """
        Generate prior authorization request.
        
        Args:
            patient_id: Patient ID
            service: Service/procedure requiring prior auth
            diagnosis: Diagnosis code/description
            payer: Insurance payer name
            context: Optional clinical context
            
        Returns:
            CoworkArtifact with prior auth request
        """
        logger.info(
            "Generating prior auth",
            patient_id=patient_id,
            service=service,
            payer=payer,
        )
        
        # Gather patient context
        if not context:
            context = await self._gather_patient_context(patient_id)
        
        # Generate prior auth
        prior_auth_prompt = f"""Generate a professional prior authorization request.

PRIOR AUTH INFORMATION:
- Patient ID: {patient_id}
- Service/Procedure: {service}
- Diagnosis: {diagnosis}
- Payer: {payer}

CLINICAL CONTEXT:
{self._format_context_for_prior_auth(context)}

Generate a complete prior authorization request with:
1. Patient identification and insurance information
2. Service/procedure details (CPT codes, description)
3. Diagnosis codes (ICD-10)
4. Clinical justification and medical necessity
5. Relevant clinical history and failed treatments
6. Provider attestation
7. Request for approval

Use professional prior authorization format.
"""
        
        prior_auth_content = await self.action_agent.llm.generate(
            prompt=prior_auth_prompt,
            system_prompt="You are a healthcare administrative specialist. Generate professional prior authorization requests.",
        )
        
        # Create artifact
        artifact = CoworkArtifact(
            type=ArtifactType.PRIOR_AUTH,
            title=f"Prior Auth - {service} - {patient_id}",
            content=prior_auth_content,
            created_by="scribe_agent",
            metadata={
                "patient_id": patient_id,
                "service": service,
                "diagnosis": diagnosis,
                "payer": payer,
            },
        )
        
        return artifact
    
    # =========================================================================
    # Order Drafting (FHIR RequestGroup)
    # =========================================================================
    
    async def draft_orders(
        self,
        patient_id: str,
        order_types: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Draft orders for CPOE (Computerized Physician Order Entry).
        
        Pre-populates FHIR RequestGroup with:
        - Lab orders
        - Imaging orders
        - Medication orders
        - Procedure orders
        
        Args:
            patient_id: Patient ID
            order_types: List of order types (e.g., ["lab", "imaging", "medication"])
            context: Optional clinical context
            
        Returns:
            Dict with FHIR RequestGroup structure
        """
        logger.info(
            "Drafting orders",
            patient_id=patient_id,
            order_types=order_types,
        )
        
        # Gather patient context
        if not context:
            context = await self._gather_patient_context(patient_id)
        
        # Build RequestGroup
        request_group = {
            "resourceType": "RequestGroup",
            "status": "draft",
            "intent": "order",
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "action": [],
        }
        
        # Add actions for each order type
        for order_type in order_types:
            action = await self._create_order_action(order_type, patient_id, context)
            request_group["action"].append(action)
        
        return {
            "patient_id": patient_id,
            "request_group": request_group,
            "order_count": len(order_types),
        }
    
    async def _create_order_action(
        self,
        order_type: str,
        patient_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a FHIR action for an order type."""
        if order_type == "lab":
            return {
                "title": "Laboratory Orders",
                "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "draft",
                    "intent": "order",
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "24323-8",  # Example: Comprehensive metabolic panel
                            "display": "Comprehensive Metabolic Panel",
                        }],
                    },
                },
            }
        elif order_type == "imaging":
            return {
                "title": "Imaging Orders",
                "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "draft",
                    "intent": "order",
                    "code": {
                        "coding": [{
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": "72141",  # Example: MRI brain
                            "display": "MRI Brain",
                        }],
                    },
                },
            }
        elif order_type == "medication":
            return {
                "title": "Medication Orders",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "status": "draft",
                    "intent": "order",
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "197806",  # Example: Lisinopril
                            "display": "Lisinopril",
                        }],
                    },
                },
            }
        else:
            return {
                "title": f"{order_type} Order",
                "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "draft",
                    "intent": "order",
                },
            }
    
    # =========================================================================
    # Patient Translation (Multilingual)
    # =========================================================================
    
    async def translate_patient_instructions(
        self,
        instructions: str,
        target_language: str,
        health_literacy_level: str = "5th_grade",
    ) -> str:
        """
        Translate patient instructions to target language at specified reading level.
        
        Args:
            instructions: Original instructions (English)
            target_language: Target language code (e.g., "es", "zh", "ar", "hi")
            health_literacy_level: Reading level (e.g., "5th_grade", "8th_grade")
            
        Returns:
            Translated instructions
        """
        logger.info(
            "Translating patient instructions",
            target_language=target_language,
            health_literacy_level=health_literacy_level,
        )
        
        translation_prompt = f"""Translate these patient instructions to {target_language} at a {health_literacy_level} reading level.

ORIGINAL INSTRUCTIONS (English):
{instructions}

Requirements:
1. Translate accurately to {target_language}
2. Use simple language appropriate for {health_literacy_level} reading level
3. Maintain medical accuracy
4. Use culturally appropriate phrasing
5. Keep instructions clear and actionable

Return ONLY the translated text, nothing else.
"""
        
        translated = await self.action_agent.llm.generate(
            prompt=translation_prompt,
            system_prompt="You are a medical translator specializing in patient education materials.",
        )
        
        return translated
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    async def _gather_patient_context(self, patient_id: str) -> Dict[str, Any]:
        """Gather patient context for document generation."""
        # In production, would query Data Moat
        # For now, return empty context
        return {
            "patient_id": patient_id,
            "demographics": {},
            "conditions": [],
            "medications": [],
            "labs": [],
            "vitals": [],
        }
    
    def _format_context_for_soap(self, context: Dict[str, Any]) -> str:
        """Format context for SOAP note generation."""
        parts = []
        
        if context.get("demographics"):
            parts.append(f"Demographics: {context['demographics']}")
        if context.get("conditions"):
            parts.append(f"Conditions: {', '.join([c.get('display', '') for c in context['conditions']])}")
        if context.get("medications"):
            parts.append(f"Medications: {', '.join([m.get('display', '') for m in context['medications']])}")
        if context.get("labs"):
            parts.append(f"Recent Labs: {len(context['labs'])} results")
        if context.get("vitals"):
            parts.append(f"Vitals: {len(context['vitals'])} measurements")
        
        return "\n".join(parts) if parts else "No additional context available"
    
    def _format_context_for_referral(self, context: Dict[str, Any]) -> str:
        """Format context for referral letter generation."""
        return self._format_context_for_soap(context)
    
    def _format_context_for_prior_auth(self, context: Dict[str, Any]) -> str:
        """Format context for prior auth generation."""
        return self._format_context_for_soap(context)
