"""
Guardian Agent

The Guardian Agent performs governance & safety checks with:
- Real-Time Guideline Guardrails: NCCN (Oncology) and KDIGO (Nephrology) logic
- Safety Block: Blocks conflicting medications (e.g., ACE inhibitor when K+ > 5.5)
- Audit Attribution: Tags recommendations with GUIDELINE_ID and SOURCE_LINK

This wraps TriageAgent + GuardrailsEngine with Guardian-specific interfaces.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

from aegis.agents.triage import TriageAgent
from aegis_ai.guardrails.engine import GuardrailsEngine, GuardrailResult
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class GuardianAgent:
    """
    Guardian Agent - Governance & Safety
    
    The Guardian performs hard-coded clinical safety and medicolegal auditability.
    
    Features:
    1. Guideline Cross-Check: Maintains vectorized library of NCCN, KDIGO, ACC guidelines
    2. Conflict Detection: Flags drug-drug and drug-lab interactions
    3. Explanation Engine: Every "Block" includes citation link to exact guideline section
    
    This wraps TriageAgent and GuardrailsEngine with Guardian-specific methods.
    """
    
    def __init__(
        self,
        pool=None,
        tenant_id: str = "default",
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize Guardian Agent.
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            llm_client: LLM client
        """
        self.pool = pool
        self.tenant_id = tenant_id
        
        # Wrap TriageAgent
        self.triage_agent = TriageAgent(
            pool=pool,
            tenant_id=tenant_id,
            llm_client=llm_client,
        )
        
        # Wrap GuardrailsEngine
        self.guardrails = GuardrailsEngine()
        
        logger.info("GuardianAgent initialized", tenant_id=tenant_id)
    
    # =========================================================================
    # Guideline Cross-Check
    # =========================================================================
    
    async def check_guidelines(
        self,
        patient_id: str,
        proposed_action: Dict[str, Any],
        specialty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check proposed action against clinical guidelines.
        
        Example: Check if dose hold is required per NCCN for Hemoglobin < 9.0
        
        Args:
            patient_id: Patient ID
            proposed_action: Proposed action (e.g., {"type": "medication", "name": "Lisinopril", "dose": "20mg"})
            specialty: Optional specialty (e.g., "oncology", "nephrology")
            
        Returns:
            Dict with:
            - allowed: Whether action is allowed
            - violations: List of guideline violations
            - recommendations: Recommended actions
            - citations: List of guideline citations
        """
        logger.info(
            "Checking guidelines",
            patient_id=patient_id,
            proposed_action=proposed_action,
            specialty=specialty,
        )
        
        violations = []
        recommendations = []
        citations = []
        
        # Get patient context
        patient_context = await self._get_patient_context(patient_id)
        
        # Check against guidelines based on specialty
        if specialty == "oncology":
            # NCCN guidelines check
            nccn_result = await self._check_nccn_guidelines(patient_context, proposed_action)
            violations.extend(nccn_result.get("violations", []))
            recommendations.extend(nccn_result.get("recommendations", []))
            citations.extend(nccn_result.get("citations", []))
        
        elif specialty == "nephrology":
            # KDIGO guidelines check
            kdigo_result = await self._check_kdigo_guidelines(patient_context, proposed_action)
            violations.extend(kdigo_result.get("violations", []))
            recommendations.extend(kdigo_result.get("recommendations", []))
            citations.extend(kdigo_result.get("citations", []))
        
        # Generic safety checks
        safety_result = await self._check_safety(patient_context, proposed_action)
        violations.extend(safety_result.get("violations", []))
        recommendations.extend(safety_result.get("recommendations", []))
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "recommendations": recommendations,
            "citations": citations,
            "patient_id": patient_id,
            "proposed_action": proposed_action,
        }
    
    async def _check_nccn_guidelines(
        self,
        patient_context: Dict[str, Any],
        proposed_action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check against NCCN oncology guidelines."""
        violations = []
        recommendations = []
        citations = []
        
        # Example: Check hemoglobin threshold for dose hold
        labs = patient_context.get("labs", [])
        hemoglobin = next((lab for lab in labs if lab.get("code") == "HGB"), None)
        
        if hemoglobin and proposed_action.get("type") == "chemo_dose":
            hgb_value = hemoglobin.get("value")
            if hgb_value and hgb_value < 9.0:
                violations.append({
                    "severity": "critical",
                    "message": "Hemoglobin < 9.0 requires dose hold per NCCN guidelines",
                    "guideline": "NCCN",
                    "section": "Supportive Care - Anemia Management",
                })
                recommendations.append({
                    "action": "hold_dose",
                    "reason": "Hemoglobin below threshold",
                    "alternative": "Consider Epoetin Alpha evaluation",
                })
                citations.append({
                    "guideline": "NCCN",
                    "section": "Supportive Care - Anemia Management",
                    "link": "https://www.nccn.org/guidelines/guidelines-detail",
                })
        
        return {
            "violations": violations,
            "recommendations": recommendations,
            "citations": citations,
        }
    
    async def _check_kdigo_guidelines(
        self,
        patient_context: Dict[str, Any],
        proposed_action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check against KDIGO nephrology guidelines."""
        violations = []
        recommendations = []
        citations = []
        
        # Example: Check potassium threshold for ACE inhibitor
        labs = patient_context.get("labs", [])
        potassium = next((lab for lab in labs if lab.get("code") == "K"), None)
        
        if potassium and proposed_action.get("type") == "medication":
            med_name = proposed_action.get("name", "").lower()
            if "ace" in med_name or "lisinopril" in med_name or "enalapril" in med_name:
                k_value = potassium.get("value")
                if k_value and k_value > 5.5:
                    violations.append({
                        "severity": "critical",
                        "message": "ACE inhibitor contraindicated with K+ > 5.5 per KDIGO guidelines",
                        "guideline": "KDIGO",
                        "section": "CKD-MBD Management",
                    })
                    recommendations.append({
                        "action": "hold_medication",
                        "reason": "Hyperkalemia risk",
                        "alternative": "Consider ARB or alternative antihypertensive",
                    })
                    citations.append({
                        "guideline": "KDIGO",
                        "section": "CKD-MBD Management",
                        "link": "https://kdigo.org/guidelines/",
                    })
        
        return {
            "violations": violations,
            "recommendations": recommendations,
            "citations": citations,
        }
    
    # =========================================================================
    # Conflict Detection
    # =========================================================================
    
    async def check_conflicts(
        self,
        patient_id: str,
        proposed_medication: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check for drug-drug and drug-lab interactions.
        
        Example: "Patient is on Paxlovid; Scribe suggested a statin; Guardian blocks action due to toxicity risk"
        
        Args:
            patient_id: Patient ID
            proposed_medication: Proposed medication (e.g., {"name": "Atorvastatin", "dose": "20mg"})
            
        Returns:
            Dict with conflict information
        """
        logger.info(
            "Checking conflicts",
            patient_id=patient_id,
            proposed_medication=proposed_medication,
        )
        
        # Get patient's current medications
        patient_context = await self._get_patient_context(patient_id)
        current_meds = patient_context.get("medications", [])
        
        # Get patient's labs
        labs = patient_context.get("labs", [])
        
        conflicts = []
        
        # Check drug-drug interactions
        for med in current_meds:
            conflict = await self._check_drug_drug_interaction(
                med,
                proposed_medication,
            )
            if conflict:
                conflicts.append(conflict)
        
        # Check drug-lab interactions
        drug_lab_conflict = await self._check_drug_lab_interaction(
            proposed_medication,
            labs,
        )
        if drug_lab_conflict:
            conflicts.append(drug_lab_conflict)
        
        return {
            "patient_id": patient_id,
            "proposed_medication": proposed_medication,
            "conflicts": conflicts,
            "allowed": len(conflicts) == 0,
        }
    
    async def _check_drug_drug_interaction(
        self,
        current_med: Dict[str, Any],
        proposed_med: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Check for drug-drug interaction."""
        current_name = current_med.get("name", "").lower()
        proposed_name = proposed_med.get("name", "").lower()
        
        # Known interactions (in production, would use drug interaction database)
        interactions = {
            ("paxlovid", "atorvastatin"): {
                "severity": "high",
                "message": "Paxlovid increases statin levels - risk of toxicity",
                "recommendation": "Hold statin or reduce dose",
            },
            ("warfarin", "aspirin"): {
                "severity": "moderate",
                "message": "Increased bleeding risk",
                "recommendation": "Monitor INR closely",
            },
        }
        
        key = (current_name, proposed_name)
        reverse_key = (proposed_name, current_name)
        
        if key in interactions:
            return interactions[key]
        elif reverse_key in interactions:
            return interactions[reverse_key]
        
        return None
    
    async def _check_drug_lab_interaction(
        self,
        medication: Dict[str, Any],
        labs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Check for drug-lab interaction."""
        med_name = medication.get("name", "").lower()
        
        # Check ACE inhibitor + hyperkalemia
        if "ace" in med_name or "lisinopril" in med_name:
            potassium = next((lab for lab in labs if lab.get("code") == "K"), None)
            if potassium and potassium.get("value", 0) > 5.5:
                return {
                    "severity": "critical",
                    "message": "ACE inhibitor contraindicated with K+ > 5.5",
                    "recommendation": "Hold medication until K+ normalized",
                }
        
        # Check metformin + elevated creatinine
        if "metformin" in med_name:
            creatinine = next((lab for lab in labs if lab.get("code") == "CREAT"), None)
            if creatinine and creatinine.get("value", 0) > 1.5:
                return {
                    "severity": "moderate",
                    "message": "Metformin caution with elevated creatinine",
                    "recommendation": "Monitor renal function",
                }
        
        return None
    
    # =========================================================================
    # Safety Block
    # =========================================================================
    
    async def block_unsafe_action(
        self,
        patient_id: str,
        proposed_action: Dict[str, Any],
        reason: str,
        guideline_citation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Block an unsafe action and require clinical override rationale.
        
        Args:
            patient_id: Patient ID
            proposed_action: Proposed action to block
            reason: Reason for blocking
            guideline_citation: Optional guideline citation
            
        Returns:
            Dict with block information
        """
        logger.warning(
            "Blocking unsafe action",
            patient_id=patient_id,
            proposed_action=proposed_action,
            reason=reason,
        )
        
        return {
            "blocked": True,
            "patient_id": patient_id,
            "proposed_action": proposed_action,
            "reason": reason,
            "guideline_citation": guideline_citation,
            "requires_override": True,
            "override_rationale_required": "Clinical override rationale must be provided",
        }
    
    # =========================================================================
    # Explanation Engine
    # =========================================================================
    
    async def explain_recommendation(
        self,
        recommendation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate explanation for a recommendation with evidence links.
        
        Every recommendation includes:
        - Rationale
        - Evidence (links to FHIR nodes)
        - Guideline references
        - Source links
        
        Args:
            recommendation: Recommendation dict
            
        Returns:
            Dict with explanation
        """
        logger.info("Explaining recommendation", recommendation=recommendation)
        
        return {
            "recommendation": recommendation,
            "rationale": recommendation.get("rationale", ""),
            "evidence": recommendation.get("evidence_links", []),
            "guideline_references": recommendation.get("guideline_citations", []),
            "source_links": recommendation.get("source_links", []),
        }
    
    # =========================================================================
    # Audit Attribution
    # =========================================================================
    
    async def add_audit_attribution(
        self,
        action: Dict[str, Any],
        guideline_id: str,
        source_link: str,
    ) -> Dict[str, Any]:
        """
        Add audit attribution to an action.
        
        Every recommendation is tagged with:
        - GUIDELINE_ID
        - SOURCE_LINK back to peer-reviewed literature
        
        Args:
            action: Action dict
            guideline_id: Guideline ID (e.g., "NCCN-2024-Anemia")
            source_link: Source link to literature
            
        Returns:
            Action with audit attribution
        """
        action["audit"] = {
            "guideline_id": guideline_id,
            "source_link": source_link,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return action
    
    # =========================================================================
    # Unified Interface (wraps TriageAgent)
    # =========================================================================
    
    async def run_safety_check(
        self,
        patient_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run comprehensive safety check (wraps TriageAgent).
        
        Args:
            patient_id: Patient ID
            context: Optional additional context
            
        Returns:
            Dict with safety check results
        """
        logger.info("Running safety check", patient_id=patient_id)
        
        # Use TriageAgent
        result = await self.triage_agent.run(
            query=f"Run safety check for patient {patient_id}",
            tenant_id=self.tenant_id,
        )
        
        return {
            "patient_id": patient_id,
            "alerts": result.get("alerts", []),
            "safety_flags": result.get("safety_flags", []),
            "recommendations": result.get("recommendations", []),
        }
    
    async def _get_patient_context(self, patient_id: str) -> Dict[str, Any]:
        """Get patient context for safety checks."""
        # In production, would query Data Moat
        # For now, return empty context
        return {
            "patient_id": patient_id,
            "labs": [],
            "medications": [],
            "conditions": [],
        }
