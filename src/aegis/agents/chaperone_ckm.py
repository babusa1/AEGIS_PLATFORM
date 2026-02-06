"""
Chaperone CKM Agent

Therapeutic-specific agent for Chronic Kidney Disease (CKD) management.
Uses Data Moat + RAG (guidelines) + LLM to provide:
- Patient app: BP/weight logging, diet coaching, medication adherence
- Provider dashboard: KFRE risk prediction, eGFR trending, care gap tracking, dialysis planning

Built on top of Data Moat to demonstrate "use the data we have to build agents."
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import structlog
import math

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.data_tools import DataMoatTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class ChaperoneCKMAgent(BaseAgent):
    """
    Chaperone CKM Agent - Chronic Kidney Disease Management
    
    Specialized agent for nephrology workflows:
    - KFRE (Kidney Failure Risk Equation) calculation
    - eGFR trending and progression monitoring
    - Care gap tracking (ACR, A1C, BP control)
    - Dialysis planning triggers
    - Patient engagement (BP logging, diet coaching)
    
    Uses Data Moat to access:
    - Patient demographics (age, gender)
    - Conditions (CKD stage, diabetes, hypertension)
    - Lab results (eGFR, creatinine, ACR, albumin)
    - Medications (ACE inhibitors, ARBs, etc.)
    - Vitals (BP, weight)
    - Encounters (nephrology visits)
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
            tools.update({
                "get_entity_by_id": all_tools.get("get_entity_by_id"),
                "list_entities": all_tools.get("list_entities"),
                "get_patient_summary": all_tools.get("get_patient_summary"),
            })
        
        super().__init__(
            name="chaperone_ckm_agent",
            llm_client=llm_client,
            max_iterations=5,
            tools=tools,
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the Chaperone CKM Agent, a specialized chronic kidney disease management companion.

Your role:
1. Calculate KFRE (Kidney Failure Risk Equation) for CKD progression risk
2. Monitor eGFR trends and identify rapid progression
3. Track care gaps (ACR, A1C, BP control, vaccinations)
4. Identify dialysis planning triggers (eGFR < 15, symptoms)
5. Provide patient-facing guidance (BP logging, diet coaching, medication adherence)
6. Generate provider dashboard insights (high-risk patients, care gaps, referral needs)

Use the Data Moat tools to query:
- Patient demographics (age, gender)
- Conditions (CKD stage N18.x, diabetes, hypertension)
- Lab results (eGFR, creatinine, ACR, albumin, A1C)
- Medications (ACE inhibitors, ARBs, SGLT2 inhibitors)
- Vitals (BP, weight)
- Encounters (nephrology visits)

Always cite your data sources and provide actionable recommendations."""
    
    async def analyze_patient_ckd_status(
        self,
        patient_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze comprehensive CKD status for a patient.
        
        Returns:
            CKD status with KFRE, eGFR trends, care gaps, dialysis planning
        """
        logger.info("ChaperoneCKM: analyze_patient_ckd_status", patient_id=patient_id)
        
        if not self.data_moat:
            return {"error": "Data Moat not available"}
        
        try:
            # Get patient summary
            patient_summary = await self.data_moat.get_patient_summary(patient_id)
            patient = patient_summary.get("patient", {})
            
            # Get CKD conditions
            ckd_conditions = await self.data_moat.list_entities(
                "condition",
                filters={"patient_id": patient_id, "code": "N18"},
            )
            
            # Get all conditions (for diabetes, hypertension)
            all_conditions = patient_summary.get("conditions", [])
            
            # Get lab results (eGFR, creatinine, ACR, albumin, A1C)
            labs = await self.data_moat.list_entities(
                "lab_result",
                filters={"patient_id": patient_id},
                limit=100,
            )
            
            # Get medications
            medications = await self.data_moat.list_entities(
                "medication",
                filters={"patient_id": patient_id, "status": "active"},
            )
            
            # Get vitals (BP, weight)
            vitals = await self.data_moat.list_entities(
                "vital",
                filters={"patient_id": patient_id},
                limit=50,
            )
            
            # Get encounters
            encounters = await self.data_moat.list_entities(
                "encounter",
                filters={"patient_id": patient_id},
                limit=20,
            )
            
            # Calculate KFRE
            kfre_result = self._calculate_kfre(
                patient,
                all_conditions,
                labs.get("entities", []),
            )
            
            # Analyze eGFR trends
            egfr_trend = self._analyze_egfr_trend(labs.get("entities", []))
            
            # Identify care gaps
            care_gaps = self._identify_care_gaps(
                all_conditions,
                labs.get("entities", []),
                medications.get("entities", []),
                vitals.get("entities", []),
            )
            
            # Dialysis planning assessment
            dialysis_assessment = self._assess_dialysis_planning(
                kfre_result,
                egfr_trend,
                labs.get("entities", []),
            )
            
            return {
                "patient_id": patient_id,
                "ckd_status": {
                    "patient": patient,
                    "ckd_stage": self._determine_ckd_stage(labs.get("entities", [])),
                    "comorbidities": {
                        "diabetes": any("diabetes" in c.get("display", "").lower() for c in all_conditions),
                        "hypertension": any("hypertension" in c.get("display", "").lower() for c in all_conditions),
                    },
                    "kfre": kfre_result,
                    "egfr_trend": egfr_trend,
                    "recent_labs": self._filter_ckd_labs(labs.get("entities", []))[:10],
                    "medications": medications.get("entities", []),
                    "recent_bp": self._get_recent_bp(vitals.get("entities", [])),
                    "recent_encounters": encounters.get("entities", [])[:5],
                },
                "care_gaps": care_gaps,
                "dialysis_planning": dialysis_assessment,
                "risk_flags": self._generate_risk_flags(kfre_result, egfr_trend, dialysis_assessment),
                "recommendations": self._generate_recommendations(
                    kfre_result,
                    egfr_trend,
                    care_gaps,
                    dialysis_assessment,
                ),
            }
            
        except Exception as e:
            logger.error("analyze_patient_ckd_status failed", error=str(e))
            return {"error": str(e), "patient_id": patient_id}
    
    def _calculate_kfre(
        self,
        patient: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        labs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate Kidney Failure Risk Equation (KFRE).
        
        KFRE uses:
        - Age
        - Gender
        - eGFR
        - ACR (albumin-to-creatinine ratio)
        - Diabetes status
        
        Returns 2-year and 5-year risk of kidney failure.
        """
        # Get patient age
        age = patient.get("age")
        if not age:
            return {"error": "Age required for KFRE calculation"}
        
        # Get gender (male = 1, female = 0)
        gender = patient.get("gender", "").lower()
        is_male = 1 if gender == "male" else 0
        
        # Get most recent eGFR
        egfr_labs = [l for l in labs if "egfr" in l.get("test_name", "").lower() or l.get("test_code") == "33914-3"]
        if not egfr_labs:
            return {"error": "eGFR required for KFRE calculation"}
        
        latest_egfr = egfr_labs[-1].get("value")
        if not latest_egfr:
            return {"error": "eGFR value required"}
        
        # Get most recent ACR
        acr_labs = [l for l in labs if "acr" in l.get("test_name", "").lower() or "albumin" in l.get("test_name", "").lower()]
        acr_mg_g = None
        if acr_labs:
            # Simplified - would need proper ACR calculation
            acr_mg_g = 30  # Default if not available
        
        # Check diabetes
        has_diabetes = any("diabetes" in c.get("display", "").lower() for c in conditions)
        
        # KFRE formula (simplified version)
        # Full formula uses log transformations - this is a simplified approximation
        # In production, would use validated KFRE coefficients
        
        # Base risk factors
        age_factor = (age - 60) / 10 if age >= 60 else 0
        egfr_factor = (90 - latest_egfr) / 10
        acr_factor = math.log10(acr_mg_g / 1.0) if acr_mg_g else 0
        
        # Simplified risk score (not true KFRE, but demonstrates concept)
        risk_score = (
            age_factor * 0.1 +
            is_male * 0.1 +
            egfr_factor * 0.3 +
            acr_factor * 0.2 +
            (1 if has_diabetes else 0) * 0.2
        )
        
        # Convert to probabilities (simplified)
        risk_2yr = min(0.95, max(0.01, risk_score * 0.15))
        risk_5yr = min(0.95, max(0.01, risk_score * 0.35))
        
        return {
            "egfr": latest_egfr,
            "acr_mg_g": acr_mg_g,
            "has_diabetes": has_diabetes,
            "risk_2yr": round(risk_2yr * 100, 2),
            "risk_5yr": round(risk_5yr * 100, 2),
            "risk_category": "high" if risk_2yr > 0.20 else "moderate" if risk_2yr > 0.10 else "low",
            "calculated_at": datetime.utcnow().isoformat(),
        }
    
    def _analyze_egfr_trend(self, labs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze eGFR trend over time."""
        egfr_labs = [
            l for l in labs
            if ("egfr" in l.get("test_name", "").lower() or l.get("test_code") == "33914-3")
            and l.get("value") is not None
        ]
        
        if len(egfr_labs) < 2:
            return {
                "trend": "insufficient_data",
                "message": "Need at least 2 eGFR values to assess trend",
            }
        
        # Sort by time
        egfr_labs.sort(key=lambda x: x.get("time", datetime.min))
        
        values = [l.get("value") for l in egfr_labs]
        latest = values[-1]
        previous = values[-2] if len(values) >= 2 else values[0]
        
        # Calculate change
        change = latest - previous
        change_pct = (change / previous * 100) if previous > 0 else 0
        
        # Determine trend
        if change < -5:
            trend = "declining"
            severity = "rapid" if change < -10 else "moderate"
        elif change > 5:
            trend = "improving"
            severity = "moderate"
        else:
            trend = "stable"
            severity = "none"
        
        return {
            "trend": trend,
            "severity": severity,
            "latest_egfr": latest,
            "previous_egfr": previous,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "data_points": len(egfr_labs),
            "message": f"eGFR {trend} ({change:+.1f} mL/min/1.73m²)",
        }
    
    def _identify_care_gaps(
        self,
        conditions: List[Dict[str, Any]],
        labs: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        vitals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify CKD care gaps."""
        gaps = []
        
        # Check ACR (should be checked annually for CKD)
        acr_labs = [l for l in labs if "acr" in l.get("test_name", "").lower()]
        if not acr_labs:
            gaps.append({
                "type": "acr",
                "description": "ACR (albumin-to-creatinine ratio) not documented",
                "priority": "high",
                "recommendation": "Order ACR to assess proteinuria",
            })
        
        # Check BP control (should be < 130/80 for CKD)
        recent_bp = self._get_recent_bp(vitals)
        if recent_bp:
            systolic = recent_bp.get("systolic")
            diastolic = recent_bp.get("diastolic")
            if systolic and systolic > 130:
                gaps.append({
                    "type": "bp_control",
                    "description": f"BP elevated ({systolic}/{diastolic})",
                    "priority": "high",
                    "recommendation": "Optimize BP control (target < 130/80)",
                })
        
        # Check for ACE/ARB (should be on for CKD with proteinuria)
        has_ace_arb = any(
            "ace" in m.get("display", "").lower() or "arb" in m.get("display", "").lower()
            for m in medications
        )
        if not has_ace_arb and acr_labs:
            gaps.append({
                "type": "ace_arb",
                "description": "Not on ACE inhibitor or ARB",
                "priority": "medium",
                "recommendation": "Consider ACE inhibitor or ARB for proteinuria",
            })
        
        # Check A1C (if diabetic)
        has_diabetes = any("diabetes" in c.get("display", "").lower() for c in conditions)
        if has_diabetes:
            a1c_labs = [l for l in labs if "a1c" in l.get("test_name", "").lower() or "hba1c" in l.get("test_name", "").lower()]
            if not a1c_labs:
                gaps.append({
                    "type": "a1c",
                    "description": "A1C not documented (diabetic patient)",
                    "priority": "medium",
                    "recommendation": "Order A1C to assess diabetes control",
                })
        
        return gaps
    
    def _assess_dialysis_planning(
        self,
        kfre_result: Dict[str, Any],
        egfr_trend: Dict[str, Any],
        labs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assess dialysis planning needs."""
        latest_egfr = egfr_trend.get("latest_egfr")
        
        if not latest_egfr:
            return {"status": "unknown", "message": "eGFR not available"}
        
        # Dialysis planning triggers
        triggers = []
        
        if latest_egfr < 15:
            triggers.append({
                "type": "egfr_critical",
                "message": "eGFR < 15 - immediate dialysis planning needed",
                "priority": "critical",
            })
        elif latest_egfr < 20:
            triggers.append({
                "type": "egfr_low",
                "message": "eGFR < 20 - dialysis planning should begin",
                "priority": "high",
            })
        
        if kfre_result.get("risk_2yr", 0) > 20:
            triggers.append({
                "type": "high_kfre",
                "message": f"High 2-year KFRE risk ({kfre_result.get('risk_2yr')}%)",
                "priority": "high",
            })
        
        if egfr_trend.get("trend") == "declining" and egfr_trend.get("severity") == "rapid":
            triggers.append({
                "type": "rapid_decline",
                "message": "Rapid eGFR decline detected",
                "priority": "high",
            })
        
        return {
            "status": "needed" if triggers else "not_needed",
            "triggers": triggers,
            "recommendation": "Begin dialysis planning" if triggers else "Continue monitoring",
        }
    
    def _determine_ckd_stage(self, labs: List[Dict[str, Any]]) -> str:
        """Determine CKD stage from eGFR."""
        egfr_labs = [l for l in labs if "egfr" in l.get("test_name", "").lower() or l.get("test_code") == "33914-3"]
        if not egfr_labs:
            return "unknown"
        
        latest_egfr = egfr_labs[-1].get("value")
        if not latest_egfr:
            return "unknown"
        
        if latest_egfr >= 90:
            return "Stage 1"
        elif latest_egfr >= 60:
            return "Stage 2"
        elif latest_egfr >= 45:
            return "Stage 3a"
        elif latest_egfr >= 30:
            return "Stage 3b"
        elif latest_egfr >= 15:
            return "Stage 4"
        else:
            return "Stage 5"
    
    def _filter_ckd_labs(self, labs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter labs relevant to CKD."""
        ckd_test_codes = ["33914-3", "2160-0", "1751-7", "4548-4"]  # eGFR, creatinine, albumin, A1C
        ckd_keywords = ["egfr", "creatinine", "albumin", "acr", "a1c", "hba1c"]
        
        return [
            l for l in labs
            if l.get("test_code") in ckd_test_codes
            or any(keyword in l.get("test_name", "").lower() for keyword in ckd_keywords)
        ]
    
    def _get_recent_bp(self, vitals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get most recent blood pressure."""
        bp_vitals = [
            v for v in vitals
            if "bp" in v.get("vital_type", "").lower() or v.get("vital_type") in ["bp_systolic", "bp_diastolic"]
        ]
        if not bp_vitals:
            return None
        
        # Sort by time
        bp_vitals.sort(key=lambda x: x.get("time", datetime.min), reverse=True)
        
        # Get systolic and diastolic
        systolic = next((v.get("value") for v in bp_vitals if "systolic" in v.get("vital_type", "").lower()), None)
        diastolic = next((v.get("value") for v in bp_vitals if "diastolic" in v.get("vital_type", "").lower()), None)
        
        return {
            "systolic": systolic,
            "diastolic": diastolic,
            "time": bp_vitals[0].get("time") if bp_vitals else None,
        }
    
    def _generate_risk_flags(
        self,
        kfre_result: Dict[str, Any],
        egfr_trend: Dict[str, Any],
        dialysis_assessment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate risk flags for provider dashboard."""
        flags = []
        
        if kfre_result.get("risk_category") == "high":
            flags.append({
                "type": "high_kfre",
                "priority": "high",
                "message": f"High KFRE risk: {kfre_result.get('risk_2yr')}% 2-year risk",
            })
        
        if egfr_trend.get("trend") == "declining" and egfr_trend.get("severity") == "rapid":
            flags.append({
                "type": "rapid_egfr_decline",
                "priority": "high",
                "message": "Rapid eGFR decline detected",
            })
        
        if dialysis_assessment.get("status") == "needed":
            flags.append({
                "type": "dialysis_planning",
                "priority": "critical",
                "message": "Dialysis planning required",
            })
        
        return flags
    
    def _generate_recommendations(
        self,
        kfre_result: Dict[str, Any],
        egfr_trend: Dict[str, Any],
        care_gaps: List[Dict[str, Any]],
        dialysis_assessment: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if kfre_result.get("risk_category") == "high":
            recommendations.append("Consider nephrology referral due to high KFRE risk")
        
        if egfr_trend.get("trend") == "declining":
            recommendations.append("Monitor eGFR trend closely; consider nephrology consultation")
        
        for gap in care_gaps:
            recommendations.append(gap.get("recommendation", ""))
        
        if dialysis_assessment.get("status") == "needed":
            recommendations.append("Begin dialysis planning and patient education")
        
        return recommendations
    
    async def analyze_vital_alert(
        self,
        patient_id: str,
        vital_type: str,
        value: float,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Real-time analysis of vital sign logging.
        
        Provides alerts and recommendations based on vital values.
        
        Args:
            patient_id: Patient identifier
            vital_type: Type of vital (bp_systolic, bp_diastolic, weight, etc.)
            value: Vital value
            additional_data: Additional context (e.g., diastolic BP when logging systolic)
        
        Returns:
            Alert with risk level and recommendation
        """
        logger.info("ChaperoneCKM: analyze_vital_alert", patient_id=patient_id, vital_type=vital_type, value=value)
        
        try:
            alert_level = "none"
            message = ""
            recommendation = ""
            
            # BP analysis
            if "bp" in vital_type.lower():
                if "systolic" in vital_type.lower():
                    if value > 180:
                        alert_level = "critical"
                        message = "Severe hypertension - seek immediate medical attention"
                        recommendation = "Go to emergency room or call 911"
                    elif value > 160:
                        alert_level = "high"
                        message = "Stage 2 hypertension"
                        recommendation = "Contact your nephrologist within 24 hours"
                    elif value > 140:
                        alert_level = "moderate"
                        message = "Elevated BP"
                        recommendation = "Monitor and discuss with care team at next visit"
                    elif value < 90:
                        alert_level = "moderate"
                        message = "Low BP - possible hypotension"
                        recommendation = "Monitor for dizziness or fainting"
                
                elif "diastolic" in vital_type.lower():
                    if value > 120:
                        alert_level = "critical"
                        message = "Severe hypertension - seek immediate medical attention"
                        recommendation = "Go to emergency room or call 911"
                    elif value > 100:
                        alert_level = "high"
                        message = "Stage 2 hypertension"
                        recommendation = "Contact your nephrologist within 24 hours"
                    elif value > 90:
                        alert_level = "moderate"
                        message = "Elevated BP"
                        recommendation = "Monitor and discuss with care team"
                    elif value < 60:
                        alert_level = "moderate"
                        message = "Low BP - possible hypotension"
                        recommendation = "Monitor for dizziness"
            
            # Weight analysis (for fluid retention)
            elif "weight" in vital_type.lower():
                # Get recent weight trend
                if self.data_moat:
                    vitals = await self.data_moat.list_entities(
                        "vital",
                        filters={"patient_id": patient_id, "vital_type": "weight"},
                        limit=5,
                    )
                    weight_history = vitals.get("entities", [])
                    
                    if len(weight_history) >= 2:
                        previous_weight = weight_history[-2].get("value")
                        weight_change = value - previous_weight
                        weight_change_pct = (weight_change / previous_weight * 100) if previous_weight > 0 else 0
                        
                        # Rapid weight gain (fluid retention)
                        if weight_change > 5 or weight_change_pct > 5:
                            alert_level = "high"
                            message = f"Rapid weight gain ({weight_change:.1f} lbs) - possible fluid retention"
                            recommendation = "Contact your nephrologist - may indicate worsening kidney function"
                        elif weight_change > 2:
                            alert_level = "moderate"
                            message = f"Weight gain ({weight_change:.1f} lbs)"
                            recommendation = "Monitor for fluid retention signs (swelling, shortness of breath)"
            
            return {
                "alert_level": alert_level,
                "message": message or "Vital logged successfully",
                "recommendation": recommendation or "Continue monitoring",
                "vital_type": vital_type,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error("analyze_vital_alert failed", error=str(e))
            return {
                "alert_level": "none",
                "message": "Vital logged successfully",
                "error": str(e),
            }
