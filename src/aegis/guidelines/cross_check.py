"""
Guideline Cross-Checker

Cross-checks agent outputs against clinical guidelines.
"""

from typing import Dict, Any, List, Optional
import structlog

from aegis.guidelines.base import GuidelineType
from aegis.guidelines.retriever import GuidelineRetriever
from aegis.guidelines.nccn import NCCNGuideline
from aegis.guidelines.kdigo import KDIGOGuideline

logger = structlog.get_logger(__name__)


class GuidelineCrossChecker:
    """
    Cross-checks agent outputs against clinical guidelines.
    
    Used by GuardianAgent to validate recommendations.
    """
    
    def __init__(self, retriever: Optional[GuidelineRetriever] = None):
        """
        Initialize cross-checker.
        
        Args:
            retriever: Guideline retriever
        """
        self.retriever = retriever or GuidelineRetriever()
        
        # Load common guidelines
        self.nccn = NCCNGuideline()
        self.kdigo = KDIGOGuideline()
    
    async def check_against_guidelines(
        self,
        proposed_action: Dict[str, Any],
        patient_context: Dict[str, Any],
        specialty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check proposed action against relevant guidelines.
        
        Args:
            proposed_action: Proposed action
            patient_context: Patient clinical context
            specialty: Specialty (e.g., "oncology", "nephrology")
            
        Returns:
            Dict with guideline check results
        """
        logger.info(
            "Checking against guidelines",
            action_type=proposed_action.get("type"),
            specialty=specialty,
        )
        
        violations = []
        recommendations = []
        citations = []
        
        # Check based on specialty
        if specialty == "oncology":
            result = await self._check_nccn(proposed_action, patient_context)
            violations.extend(result.get("violations", []))
            recommendations.extend(result.get("recommendations", []))
            citations.extend(result.get("citations", []))
        
        elif specialty == "nephrology":
            result = await self._check_kdigo(proposed_action, patient_context)
            violations.extend(result.get("violations", []))
            recommendations.extend(result.get("recommendations", []))
            citations.extend(result.get("citations", []))
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "recommendations": recommendations,
            "citations": citations,
            "specialty": specialty,
        }
    
    async def _check_nccn(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check against NCCN guidelines."""
        violations = []
        recommendations = []
        citations = []
        
        # Check dose hold criteria
        if action.get("type") == "chemo_dose":
            labs = context.get("labs", {})
            result = self.nccn.check_dose_hold_criteria(labs)
            
            if result["requires_hold"]:
                violations.extend(result["recommendations"])
                citations.append({
                    "guideline": "NCCN",
                    "section": "Anemia/Neutropenia Management",
                    "link": "https://www.nccn.org/guidelines/guidelines-detail",
                })
        
        return {
            "violations": violations,
            "recommendations": recommendations,
            "citations": citations,
        }
    
    async def _check_kdigo(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check against KDIGO guidelines."""
        violations = []
        recommendations = []
        citations = []
        
        # Check medication contraindications
        if action.get("type") == "medication":
            medication_name = action.get("name", "")
            labs = context.get("labs", {})
            
            result = self.kdigo.check_medication_contraindication(medication_name, labs)
            
            if result["contraindicated"]:
                violations.append({
                    "severity": "critical",
                    "message": result["reason"],
                    "guideline": "KDIGO",
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
