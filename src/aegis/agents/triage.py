"""
Triage Agent

Clinical monitoring agent that identifies patients requiring attention
based on real-time analysis of the Data Moat.

Monitors:
- Abnormal lab values
- Concerning vital signs
- Medication interactions
- Care gaps
- High-risk patient alerts
"""

from typing import Literal
from datetime import datetime
from enum import Enum

import structlog
from langgraph.graph import StateGraph, END

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.data_tools import DataMoatTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class AlertPriority(str, Enum):
    """Priority levels for clinical alerts."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertType(str, Enum):
    """Types of clinical alerts."""
    CRITICAL_LAB = "critical_lab"
    ABNORMAL_LAB = "abnormal_lab"
    VITAL_SIGN = "vital_sign"
    HIGH_RISK = "high_risk"
    CARE_GAP = "care_gap"
    MEDICATION = "medication"


class TriageState(AgentState):
    """State for triage agent."""
    alerts: list[dict]
    patients_reviewed: int
    priority_counts: dict[str, int]
    recommendations: list[str]


class TriageAgent(BaseAgent):
    """
    Clinical Triage Agent
    
    Continuously monitors patient data from the Data Moat to identify:
    1. Critical lab values requiring immediate attention
    2. Abnormal vital signs
    3. High-risk patients based on multiple factors
    4. Patients with care gaps
    
    Use Cases:
    - "Run daily triage" → Scans all patients for alerts
    - "Check critical alerts" → Returns highest priority items
    - "Review high-risk patients" → Focused analysis on at-risk population
    """
    
    def __init__(
        self,
        pool,
        tenant_id: str = "default",
        llm_client: LLMClient | None = None,
    ):
        self.pool = pool
        self.tenant_id = tenant_id
        self.data_tools = DataMoatTools(pool, tenant_id) if pool else None
        
        super().__init__(
            name="triage_agent",
            llm_client=llm_client,
            max_iterations=5,
            tools={},
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the AEGIS Triage Agent, specialized in clinical monitoring
and patient safety.

Your responsibilities:
1. Monitor patient data for concerning patterns
2. Generate prioritized alerts for clinical staff
3. Identify high-risk patients requiring intervention
4. Recommend appropriate follow-up actions

Alert Priority Guidelines:
- CRITICAL: Requires immediate attention (within 1 hour)
- HIGH: Requires attention within 4 hours
- MEDIUM: Requires attention within 24 hours
- LOW: Routine follow-up needed

Always provide actionable recommendations with clinical context.
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the triage workflow."""
        workflow = StateGraph(TriageState)
        
        # Add nodes
        workflow.add_node("scan_labs", self._scan_labs)
        workflow.add_node("scan_vitals", self._scan_vitals)
        workflow.add_node("check_high_risk", self._check_high_risk)
        workflow.add_node("prioritize", self._prioritize)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        
        # Define flow
        workflow.set_entry_point("scan_labs")
        workflow.add_edge("scan_labs", "scan_vitals")
        workflow.add_edge("scan_vitals", "check_high_risk")
        workflow.add_edge("check_high_risk", "prioritize")
        workflow.add_edge("prioritize", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow
    
    async def _scan_labs(self, state: TriageState) -> dict:
        """Scan for abnormal/critical lab values."""
        if not self.data_tools:
            return {
                "alerts": [],
                "reasoning": ["Data tools not available"],
            }
        
        try:
            attention = await self.data_tools.get_patients_needing_attention()
            
            alerts = []
            for patient in attention.get("patients_with_abnormal_labs", []):
                alerts.append({
                    "type": AlertType.CRITICAL_LAB.value if patient.get("priority") == "critical" else AlertType.ABNORMAL_LAB.value,
                    "priority": patient.get("priority", "medium"),
                    "patient_id": patient["patient_id"],
                    "patient_name": patient["name"],
                    "mrn": patient["mrn"],
                    "description": f"{patient['test']}: {patient['value']} ({patient.get('interpretation', 'abnormal')})",
                    "detected_at": patient.get("time"),
                    "source": "timescaledb",
                })
            
            return {
                "alerts": alerts,
                "reasoning": [f"Found {len(alerts)} lab-related alerts"],
            }
            
        except Exception as e:
            logger.error("Lab scan failed", error=str(e))
            return {"alerts": [], "reasoning": [f"Lab scan error: {str(e)}"]}
    
    async def _scan_vitals(self, state: TriageState) -> dict:
        """Scan for concerning vital signs."""
        if not self.data_tools:
            return {"alerts": [], "reasoning": ["Data tools not available"]}
        
        try:
            attention = await self.data_tools.get_patients_needing_attention()
            
            alerts = []
            for patient in attention.get("patients_with_concerning_vitals", []):
                vital_type = patient.get("vital", "")
                value = patient.get("value", "")
                
                # Determine severity
                priority = "high"
                if "spo2" in vital_type and float(value.split()[0]) < 90:
                    priority = "critical"
                elif "bp_systolic" in vital_type and float(value.split()[0]) > 180:
                    priority = "critical"
                
                alerts.append({
                    "type": AlertType.VITAL_SIGN.value,
                    "priority": priority,
                    "patient_id": patient["patient_id"],
                    "patient_name": patient["name"],
                    "mrn": patient["mrn"],
                    "description": f"Concerning {vital_type}: {value}",
                    "detected_at": patient.get("time"),
                    "source": "timescaledb",
                })
            
            return {
                "alerts": alerts,
                "reasoning": [f"Found {len(alerts)} vital sign alerts"],
            }
            
        except Exception as e:
            logger.error("Vital scan failed", error=str(e))
            return {"alerts": [], "reasoning": [f"Vital scan error: {str(e)}"]}
    
    async def _check_high_risk(self, state: TriageState) -> dict:
        """Check for high-risk patients."""
        if not self.data_tools:
            return {"alerts": [], "reasoning": ["Data tools not available"]}
        
        try:
            high_risk = await self.data_tools.get_high_risk_patients(limit=10)
            
            alerts = []
            for patient in high_risk.get("high_risk_patients", []):
                if patient.get("risk_score", 0) >= 5:  # Threshold for alert
                    priority = "critical" if patient["risk_score"] >= 8 else "high"
                    
                    alerts.append({
                        "type": AlertType.HIGH_RISK.value,
                        "priority": priority,
                        "patient_id": patient["id"],
                        "patient_name": patient["name"],
                        "mrn": patient["mrn"],
                        "description": f"High risk score: {patient['risk_score']} - {', '.join(patient.get('risk_factors', [])[:3])}",
                        "risk_score": patient["risk_score"],
                        "risk_factors": patient.get("risk_factors", []),
                        "source": "postgresql",
                    })
            
            return {
                "alerts": alerts,
                "patients_reviewed": high_risk.get("total_found", 0),
                "reasoning": [f"Identified {len(alerts)} high-risk patient alerts"],
            }
            
        except Exception as e:
            logger.error("High-risk check failed", error=str(e))
            return {"alerts": [], "reasoning": [f"High-risk check error: {str(e)}"]}
    
    async def _prioritize(self, state: TriageState) -> dict:
        """Prioritize and deduplicate alerts."""
        all_alerts = state.get("alerts", [])
        
        # Deduplicate by patient
        seen_patients = {}
        unique_alerts = []
        
        for alert in all_alerts:
            patient_id = alert.get("patient_id")
            existing = seen_patients.get(patient_id)
            
            if not existing:
                seen_patients[patient_id] = alert
                unique_alerts.append(alert)
            else:
                # Keep higher priority alert
                priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                if priority_order.get(alert.get("priority"), 3) < priority_order.get(existing.get("priority"), 3):
                    seen_patients[patient_id] = alert
                    unique_alerts = [a for a in unique_alerts if a.get("patient_id") != patient_id]
                    unique_alerts.append(alert)
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique_alerts.sort(key=lambda x: priority_order.get(x.get("priority"), 3))
        
        # Count by priority
        priority_counts = {
            "critical": len([a for a in unique_alerts if a.get("priority") == "critical"]),
            "high": len([a for a in unique_alerts if a.get("priority") == "high"]),
            "medium": len([a for a in unique_alerts if a.get("priority") == "medium"]),
            "low": len([a for a in unique_alerts if a.get("priority") == "low"]),
        }
        
        return {
            "alerts": unique_alerts,
            "priority_counts": priority_counts,
            "reasoning": [f"Prioritized {len(unique_alerts)} unique patient alerts"],
        }
    
    async def _generate_recommendations(self, state: TriageState) -> dict:
        """Generate clinical recommendations."""
        alerts = state.get("alerts", [])
        priority_counts = state.get("priority_counts", {})
        
        recommendations = []
        
        # Critical alerts
        critical_count = priority_counts.get("critical", 0)
        if critical_count > 0:
            recommendations.append(f"🚨 IMMEDIATE: {critical_count} patients require immediate clinical review")
        
        # High priority
        high_count = priority_counts.get("high", 0)
        if high_count > 0:
            recommendations.append(f"⚠️ URGENT: {high_count} patients need attention within 4 hours")
        
        # Specific recommendations based on alert types
        lab_alerts = [a for a in alerts if a.get("type") in [AlertType.CRITICAL_LAB.value, AlertType.ABNORMAL_LAB.value]]
        if lab_alerts:
            recommendations.append(f"📋 Review {len(lab_alerts)} patients with abnormal lab values")
        
        vital_alerts = [a for a in alerts if a.get("type") == AlertType.VITAL_SIGN.value]
        if vital_alerts:
            recommendations.append(f"💓 Monitor {len(vital_alerts)} patients with concerning vitals")
        
        high_risk_alerts = [a for a in alerts if a.get("type") == AlertType.HIGH_RISK.value]
        if high_risk_alerts:
            recommendations.append(f"📊 Schedule care coordination for {len(high_risk_alerts)} high-risk patients")
        
        if not alerts:
            recommendations.append("✅ No critical alerts at this time")
        
        # Build final answer
        summary_lines = [
            "## Clinical Triage Report",
            f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"\n### Alert Summary:",
            f"- Critical: {priority_counts.get('critical', 0)}",
            f"- High: {priority_counts.get('high', 0)}",
            f"- Medium: {priority_counts.get('medium', 0)}",
            f"- Low: {priority_counts.get('low', 0)}",
            f"\n### Recommendations:",
        ]
        summary_lines.extend([f"- {r}" for r in recommendations])
        
        if alerts:
            summary_lines.append("\n### Top Priority Patients:")
            for alert in alerts[:5]:
                summary_lines.append(f"- **{alert.get('patient_name')}** ({alert.get('mrn')}): {alert.get('description')}")
        
        return {
            "recommendations": recommendations,
            "final_answer": "\n".join(summary_lines),
            "confidence": 0.95,
            "reasoning": [f"Generated {len(recommendations)} recommendations"],
        }
    
    async def run(self, query: str = "Run triage scan", user_id: str | None = None) -> dict:
        """
        Run the triage agent.
        
        Args:
            query: Optional query (default runs full scan)
            user_id: Optional user ID
            
        Returns:
            Triage report with alerts and recommendations
        """
        initial_state: TriageState = {
            "messages": [],
            "current_input": query,
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "tool_calls": [],
            "tool_results": [],
            "reasoning": [],
            "plan": [],
            "final_answer": None,
            "confidence": 0.0,
            "alerts": [],
            "patients_reviewed": 0,
            "priority_counts": {},
            "recommendations": [],
        }
        
        try:
            graph = self._build_graph()
            compiled = graph.compile()
            
            final_state = None
            async for state in compiled.astream(initial_state):
                final_state = state
            
            if final_state:
                # Extract from nested state
                all_alerts = []
                all_recommendations = []
                priority_counts = {}
                final_answer = None
                confidence = 0.0
                
                for node_name, node_state in final_state.items():
                    if isinstance(node_state, dict):
                        all_alerts.extend(node_state.get("alerts", []))
                        all_recommendations.extend(node_state.get("recommendations", []))
                        if node_state.get("priority_counts"):
                            priority_counts = node_state["priority_counts"]
                        if node_state.get("final_answer"):
                            final_answer = node_state["final_answer"]
                        if node_state.get("confidence"):
                            confidence = node_state["confidence"]
                
                return {
                    "report": final_answer or "Triage complete",
                    "alerts": all_alerts,
                    "priority_counts": priority_counts,
                    "recommendations": all_recommendations,
                    "confidence": confidence,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            
            return {"report": "Triage scan complete", "alerts": []}
            
        except Exception as e:
            logger.error("Triage agent failed", error=str(e))
            return {
                "report": f"Triage error: {str(e)}",
                "alerts": [],
                "error": str(e),
            }
