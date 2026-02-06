"""
Oncolife Agent

Therapeutic-specific agent for oncology care management.
Uses Data Moat + RAG (guidelines) + LLM to provide:
- Patient app: symptom triage, medication reminders, side effect management
- Provider dashboard: risk flags, adherence metrics, genomic variant actionability, care gap alerts

Built on top of Data Moat to demonstrate "use the data we have to build agents."
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import structlog

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.data_tools import DataMoatTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class OncolifeAgent(BaseAgent):
    """
    Oncolife Agent - Oncology Care Companion
    
    Specialized agent for oncology workflows:
    - Genomic variant analysis (BRCA, EGFR, etc.)
    - Chemotherapy regimen tracking
    - Toxicity monitoring and triage
    - Tumor board preparation
    - Care gap alerts (scans, labs)
    
    Uses Data Moat to access:
    - Patient demographics, conditions, medications
    - Genomic reports (FoundationOne, Tempus)
    - Lab results (tumor markers, CBC, CMP)
    - Encounters (chemo visits, scans)
    - Observations (toxicity grades)
    """
    
    def __init__(
        self,
        tenant_id: str,
        data_moat_tools: Optional[DataMoatTools] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.tenant_id = tenant_id
        self.data_moat = data_moat_tools
        
        # Get tools from Data Moat
        tools = {}
        if self.data_moat:
            all_tools = self.data_moat.get_all_tools()
            # Use generic entity queries + specific tools
            tools.update({
                "get_entity_by_id": all_tools.get("get_entity_by_id"),
                "list_entities": all_tools.get("list_entities"),
                "get_patient_summary": all_tools.get("get_patient_summary"),
            })
        
        super().__init__(
            name="oncolife_agent",
            llm_client=llm_client,
            max_iterations=5,
            tools=tools,
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the Oncolife Agent, a specialized oncology care companion.

Your role:
1. Analyze patient oncology data from the Data Moat (genomics, chemo regimens, labs, encounters)
2. Identify genomic variants and their actionability
3. Monitor chemotherapy toxicity and side effects
4. Track care gaps (missing scans, labs, tumor board reviews)
5. Provide patient-facing guidance (symptom triage, medication reminders)
6. Generate provider dashboard insights (risk flags, adherence metrics)

Use the Data Moat tools to query:
- Patient demographics and conditions (cancer diagnoses)
- Genomic reports and variants
- Medications (chemo regimens)
- Lab results (tumor markers, CBC, CMP)
- Encounters (chemo visits, imaging studies)
- Observations (toxicity grades)

Always cite your data sources and provide actionable recommendations."""
    
    async def analyze_patient_oncology_status(
        self,
        patient_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze comprehensive oncology status for a patient.
        
        Returns:
            Oncology status with genomics, chemo, toxicity, care gaps
        """
        logger.info("Oncolife: analyze_patient_oncology_status", patient_id=patient_id)
        
        if not self.data_moat:
            return {"error": "Data Moat not available"}
        
        try:
            # Get patient summary
            patient_summary = await self.data_moat.get_patient_summary(patient_id)
            
            # Get genomic reports
            genomic_reports = await self.data_moat.list_entities(
                "genomic_report",
                filters={"patient_id": patient_id},
            )
            
            # Get genomic variants
            variants = await self.data_moat.list_entities(
                "genomic_variant",
                filters={"patient_id": patient_id},
            )
            
            # Get medications (chemo regimens)
            medications = await self.data_moat.list_entities(
                "medication",
                filters={"patient_id": patient_id, "status": "active"},
            )
            
            # Get recent labs (tumor markers, CBC, CMP)
            labs = await self.data_moat.list_entities(
                "lab_result",
                filters={"patient_id": patient_id},
                limit=50,
            )
            
            # Get encounters (chemo visits)
            encounters = await self.data_moat.list_entities(
                "encounter",
                filters={"patient_id": patient_id},
                limit=20,
            )
            
            # Analyze toxicity
            toxicity_analysis = self._analyze_toxicity(labs.get("entities", []))
            
            # Identify care gaps
            care_gaps = self._identify_care_gaps(
                patient_summary,
                genomic_reports.get("entities", []),
                medications.get("entities", []),
                labs.get("entities", []),
                encounters.get("entities", []),
            )
            
            # Genomic variant actionability
            variant_actionability = self._assess_variant_actionability(
                variants.get("entities", []),
            )
            
            return {
                "patient_id": patient_id,
                "oncology_status": {
                    "patient": patient_summary.get("patient"),
                    "cancer_diagnoses": [
                        c for c in patient_summary.get("conditions", [])
                        if any(keyword in c.get("display", "").lower() 
                               for keyword in ["cancer", "carcinoma", "tumor", "neoplasm"])
                    ],
                    "genomic_reports": genomic_reports.get("entities", []),
                    "actionable_variants": variant_actionability,
                    "active_chemo_regimens": medications.get("entities", []),
                    "recent_labs": labs.get("entities", [])[:10],  # Last 10
                    "recent_encounters": encounters.get("entities", [])[:5],
                    "toxicity_analysis": toxicity_analysis,
                    "care_gaps": care_gaps,
                },
                "risk_flags": self._generate_risk_flags(toxicity_analysis, care_gaps),
                "recommendations": self._generate_recommendations(
                    variant_actionability,
                    toxicity_analysis,
                    care_gaps,
                ),
            }
            
        except Exception as e:
            logger.error("analyze_patient_oncology_status failed", error=str(e))
            return {"error": str(e), "patient_id": patient_id}
    
    def _analyze_toxicity(self, labs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze chemotherapy toxicity from lab results."""
        # Simplified toxicity analysis
        # In production, would use CTCAE grading
        
        toxicity_findings = []
        
        for lab in labs:
            test_name = lab.get("test_name", "").lower()
            value = lab.get("value")
            abnormal = lab.get("abnormal", False)
            
            if abnormal:
                if "neutrophil" in test_name or "wbc" in test_name:
                    if value and value < 1.5:
                        toxicity_findings.append({
                            "type": "neutropenia",
                            "grade": "severe" if value < 0.5 else "moderate",
                            "test": test_name,
                            "value": value,
                            "recommendation": "Consider G-CSF support",
                        })
                
                elif "platelet" in test_name:
                    if value and value < 50:
                        toxicity_findings.append({
                            "type": "thrombocytopenia",
                            "grade": "severe" if value < 20 else "moderate",
                            "test": test_name,
                            "value": value,
                            "recommendation": "Monitor for bleeding risk",
                        })
                
                elif "creatinine" in test_name or "egfr" in test_name:
                    if "creatinine" in test_name and value and value > 2.0:
                        toxicity_findings.append({
                            "type": "renal_toxicity",
                            "grade": "moderate",
                            "test": test_name,
                            "value": value,
                            "recommendation": "Consider dose adjustment",
                        })
        
        return {
            "findings": toxicity_findings,
            "severity": "severe" if any(f.get("grade") == "severe" for f in toxicity_findings) else "moderate" if toxicity_findings else "none",
        }
    
    def _identify_care_gaps(
        self,
        patient_summary: Dict[str, Any],
        genomic_reports: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        labs: List[Dict[str, Any]],
        encounters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify care gaps (missing scans, labs, tumor board reviews)."""
        gaps = []
        
        # Check for recent imaging (should be within 3 months for active treatment)
        if medications:  # On active chemo
            recent_imaging = [
                e for e in encounters
                if "scan" in e.get("encounter_type", "").lower() or "imaging" in e.get("encounter_type", "").lower()
            ]
            if not recent_imaging:
                gaps.append({
                    "type": "imaging",
                    "description": "No recent imaging study documented",
                    "priority": "high",
                    "recommendation": "Schedule imaging per protocol",
                })
        
        # Check for tumor markers (if applicable)
        tumor_markers = [l for l in labs if any(marker in l.get("test_name", "").lower() 
                                                 for marker in ["cea", "ca19-9", "psa", "ca125"])]
        if not tumor_markers:
            gaps.append({
                "type": "tumor_markers",
                "description": "No tumor marker labs documented",
                "priority": "medium",
                "recommendation": "Consider tumor marker panel",
            })
        
        # Check for genomic testing (if cancer diagnosis but no genomics)
        cancer_diagnoses = [
            c for c in patient_summary.get("conditions", [])
            if any(keyword in c.get("display", "").lower() 
                   for keyword in ["cancer", "carcinoma", "tumor"])
        ]
        if cancer_diagnoses and not genomic_reports:
            gaps.append({
                "type": "genomic_testing",
                "description": "Cancer diagnosis but no genomic testing documented",
                "priority": "high",
                "recommendation": "Consider genomic profiling (FoundationOne, Tempus)",
            })
        
        return gaps
    
    def _assess_variant_actionability(
        self,
        variants: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Assess genomic variant actionability."""
        actionable = []
        
        # Simplified - in production would use knowledge bases
        actionable_genes = ["BRCA1", "BRCA2", "EGFR", "ALK", "BRAF", "PDL1", "MSI"]
        
        for variant in variants:
            gene = variant.get("gene", "").upper()
            if gene in actionable_genes:
                actionable.append({
                    "gene": gene,
                    "variant": variant.get("variant", ""),
                    "actionability": "high" if gene in ["BRCA1", "BRCA2", "EGFR"] else "moderate",
                    "therapies": self._get_therapies_for_gene(gene),
                    "evidence_level": "A" if gene in ["BRCA1", "BRCA2"] else "B",
                })
        
        return actionable
    
    def _get_therapies_for_gene(self, gene: str) -> List[str]:
        """Get recommended therapies for actionable gene."""
        # Simplified - in production would query RAG/knowledge base
        therapy_map = {
            "BRCA1": ["PARP inhibitors (olaparib, talazoparib)"],
            "BRCA2": ["PARP inhibitors (olaparib, talazoparib)"],
            "EGFR": ["EGFR TKIs (erlotinib, gefitinib, osimertinib)"],
            "ALK": ["ALK inhibitors (crizotinib, alectinib)"],
            "BRAF": ["BRAF inhibitors (vemurafenib, dabrafenib)"],
            "PDL1": ["Immune checkpoint inhibitors (pembrolizumab, nivolumab)"],
            "MSI": ["Immune checkpoint inhibitors (pembrolizumab)"],
        }
        return therapy_map.get(gene.upper(), [])
    
    def _generate_risk_flags(
        self,
        toxicity_analysis: Dict[str, Any],
        care_gaps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate risk flags for provider dashboard."""
        flags = []
        
        if toxicity_analysis.get("severity") == "severe":
            flags.append({
                "type": "severe_toxicity",
                "priority": "critical",
                "message": "Severe chemotherapy toxicity detected",
            })
        
        high_priority_gaps = [g for g in care_gaps if g.get("priority") == "high"]
        if high_priority_gaps:
            flags.append({
                "type": "care_gaps",
                "priority": "high",
                "message": f"{len(high_priority_gaps)} high-priority care gaps identified",
            })
        
        return flags
    
    def _generate_recommendations(
        self,
        variant_actionability: List[Dict[str, Any]],
        toxicity_analysis: Dict[str, Any],
        care_gaps: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if variant_actionability:
            recommendations.append(
                f"Consider targeted therapy based on {len(variant_actionability)} actionable variant(s)"
            )
        
        if toxicity_analysis.get("severity") != "none":
            recommendations.append("Monitor toxicity closely; consider supportive care")
        
        for gap in care_gaps:
            recommendations.append(gap.get("recommendation", ""))
        
        return recommendations
    
    async def consult_symptom_context(
        self,
        patient_id: str,
        symptom: str,
        patient_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Real-time consultation during symptom checker session.
        
        Provides context-aware insights:
        - Is this symptom expected for their chemo regimen?
        - What's the risk level given their current labs?
        - Has this patient reported similar symptoms before?
        
        Args:
            patient_id: Patient identifier
            symptom: Current symptom being discussed
            patient_context: Pre-loaded patient context (chemo, labs, variants, etc.)
        
        Returns:
            Agent insight with risk assessment and context
        """
        logger.info("Oncolife: consult_symptom_context", patient_id=patient_id, symptom=symptom)
        
        try:
            chemo_regimens = patient_context.get("chemo_regimens", [])
            recent_labs = patient_context.get("recent_labs", [])
            previous_symptoms = patient_context.get("previous_symptoms", [])
            
            # Check if symptom is expected for current regimen
            expected_symptoms = []
            for regimen in chemo_regimens:
                regimen_name = regimen.get("display", "").lower()
                # Map regimens to expected symptoms
                if "folfox" in regimen_name:
                    expected_symptoms.extend(["neuropathy", "diarrhea", "nausea"])
                elif "folfiri" in regimen_name:
                    expected_symptoms.extend(["diarrhea", "nausea", "mouth_sores"])
                elif "taxol" in regimen_name or "paclitaxel" in regimen_name:
                    expected_symptoms.extend(["neuropathy", "hair_loss"])
                elif "keytruda" in regimen_name or "pembrolizumab" in regimen_name:
                    expected_symptoms.extend(["rash", "fatigue", "diarrhea"])
            
            is_expected = any(symptom.lower() in exp.lower() or exp.lower() in symptom.lower() 
                            for exp in expected_symptoms)
            
            # Assess risk based on labs
            risk_level = "low"
            risk_factors = []
            
            # Check for neutropenia (fever + neutropenia = emergency)
            if symptom.lower() in ["fever", "temperature"]:
                neutrophil_labs = [l for l in recent_labs if "neutrophil" in l.get("test_name", "").lower()]
                if neutrophil_labs:
                    latest_neutrophil = neutrophil_labs[-1].get("value")
                    if latest_neutrophil and latest_neutrophil < 1.0:
                        risk_level = "high"
                        risk_factors.append("Neutropenia detected - febrile neutropenia risk")
            
            # Check for thrombocytopenia (bleeding risk)
            if symptom.lower() in ["bleeding", "bruising", "nosebleed"]:
                platelet_labs = [l for l in recent_labs if "platelet" in l.get("test_name", "").lower()]
                if platelet_labs:
                    latest_platelet = platelet_labs[-1].get("value")
                    if latest_platelet and latest_platelet < 50:
                        risk_level = "high"
                        risk_factors.append("Thrombocytopenia detected - bleeding risk")
            
            # Check historical patterns
            similar_symptoms = [
                s for s in previous_symptoms
                if symptom.lower() in s.get("display", "").lower() or 
                   s.get("display", "").lower() in symptom.lower()
            ]
            
            return {
                "symptom": symptom,
                "is_expected_for_regimen": is_expected,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "historical_pattern": {
                    "has_occurred_before": len(similar_symptoms) > 0,
                    "previous_occurrences": len(similar_symptoms),
                },
                "context": {
                    "active_regimens": [r.get("display") for r in chemo_regimens],
                    "recent_lab_concerns": [
                        l.get("test_name") for l in recent_labs 
                        if l.get("abnormal", False)
                    ][:3],  # Top 3 abnormal labs
                },
                "recommendation": self._generate_symptom_recommendation(
                    symptom, is_expected, risk_level, risk_factors
                ),
            }
            
        except Exception as e:
            logger.error("consult_symptom_context failed", error=str(e))
            return {
                "symptom": symptom,
                "error": str(e),
            }
    
    def _generate_symptom_recommendation(
        self,
        symptom: str,
        is_expected: bool,
        risk_level: str,
        risk_factors: List[str],
    ) -> str:
        """Generate recommendation based on symptom context."""
        if risk_level == "high":
            return f"This {symptom} combined with your recent lab results requires immediate medical attention. Please contact your care team or go to the emergency room."
        elif is_expected:
            return f"This {symptom} is a known side effect of your current treatment. Continue monitoring and follow your care team's guidance."
        else:
            return f"Please continue with the symptom checker to assess the severity of this {symptom}."
