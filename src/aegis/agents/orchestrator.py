"""
Orchestrator Agent

Master agent that coordinates multiple specialized agents and demonstrates
how the Data Moat powers intelligent healthcare operations.

The Orchestrator can:
1. Route queries to appropriate specialist agents
2. Coordinate multi-agent workflows
3. Aggregate insights from multiple sources
4. Demonstrate the power of the unified data layer
"""

from typing import Literal, Any
from datetime import datetime
from enum import Enum

import structlog
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.data_tools import DataMoatTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    """Types of tasks the orchestrator can handle."""
    PATIENT_REVIEW = "patient_review"
    DENIAL_MANAGEMENT = "denial_management"
    CLINICAL_TRIAGE = "clinical_triage"
    REVENUE_ANALYSIS = "revenue_analysis"
    CARE_COORDINATION = "care_coordination"


class AgentActivity(BaseModel):
    """Record of agent activity for visualization."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: str
    action: str
    data_sources: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    duration_ms: int = 0


class OrchestratorState(AgentState):
    """Extended state for orchestrator."""
    task_type: str | None
    sub_agents_called: list[str]
    agent_activities: list[dict]
    data_moat_queries: list[dict]
    aggregated_insights: list[str]


class OrchestratorAgent(BaseAgent):
    """
    Master Orchestrator Agent
    
    Demonstrates the AEGIS platform capabilities:
    - Multi-agent coordination
    - Data Moat integration
    - Intelligent routing
    - Insight aggregation
    
    Use Cases:
    1. "Review patient-001" → Coordinates patient data gathering + risk analysis
    2. "Handle denial backlog" → Coordinates denial analysis + appeal prioritization
    3. "Daily triage report" → Coordinates clinical monitoring + alert generation
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
            name="orchestrator",
            llm_client=llm_client,
            max_iterations=10,
            tools={},  # Orchestrator uses data_tools directly
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the AEGIS Orchestrator Agent, the master coordinator for 
healthcare operations intelligence.

Your role is to:
1. Understand the user's intent and classify the task type
2. Coordinate data gathering from the Data Moat (PostgreSQL, TimescaleDB, Graph DB)
3. Invoke specialized sub-agents when needed
4. Synthesize insights from multiple data sources
5. Provide actionable recommendations

You have access to comprehensive healthcare data including:
- Patient demographics, conditions, medications
- Clinical encounters and procedures
- Claims and denials
- Real-time vitals and lab results
- Care relationships and pathways

Always explain which data sources you're accessing and why.
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the orchestrator workflow."""
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("classify_task", self._classify_task)
        workflow.add_node("gather_data", self._gather_data)
        workflow.add_node("analyze", self._analyze)
        workflow.add_node("coordinate_agents", self._coordinate_agents)
        workflow.add_node("synthesize", self._synthesize)
        workflow.add_node("respond", self._respond)
        
        # Define flow
        workflow.set_entry_point("classify_task")
        workflow.add_edge("classify_task", "gather_data")
        workflow.add_edge("gather_data", "analyze")
        
        # Conditional: need sub-agents?
        workflow.add_conditional_edges(
            "analyze",
            self._needs_sub_agents,
            {
                "yes": "coordinate_agents",
                "no": "synthesize",
            }
        )
        workflow.add_edge("coordinate_agents", "synthesize")
        workflow.add_edge("synthesize", "respond")
        workflow.add_edge("respond", END)
        
        return workflow
    
    def _needs_sub_agents(self, state: OrchestratorState) -> Literal["yes", "no"]:
        """Determine if we need to invoke sub-agents."""
        task_type = state.get("task_type")
        # For denial management, invoke action agent for appeals
        if task_type == TaskType.DENIAL_MANAGEMENT.value:
            return "yes"
        return "no"
    
    async def _classify_task(self, state: OrchestratorState) -> dict:
        """Classify the incoming request."""
        query = state.get("current_input", "").lower()
        
        # Simple classification based on keywords
        task_type = TaskType.PATIENT_REVIEW.value
        
        if any(w in query for w in ["denial", "appeal", "claim", "rejected"]):
            task_type = TaskType.DENIAL_MANAGEMENT.value
        elif any(w in query for w in ["triage", "alert", "critical", "monitor", "attention"]):
            task_type = TaskType.CLINICAL_TRIAGE.value
        elif any(w in query for w in ["revenue", "financial", "collection", "payment"]):
            task_type = TaskType.REVENUE_ANALYSIS.value
        elif any(w in query for w in ["coordinate", "care", "team", "handoff"]):
            task_type = TaskType.CARE_COORDINATION.value
        
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "orchestrator",
            "action": "classify_task",
            "data_sources": [],
            "input_summary": query[:100],
            "output_summary": f"Task classified as: {task_type}",
        }
        
        return {
            "task_type": task_type,
            "agent_activities": [activity],
            "reasoning": [f"Classified task as: {task_type}"],
        }
    
    async def _gather_data(self, state: OrchestratorState) -> dict:
        """Gather relevant data from the Data Moat."""
        task_type = state.get("task_type")
        query = state.get("current_input", "")
        activities = []
        data_queries = []
        tool_results = []
        
        if not self.data_tools:
            return {
                "agent_activities": [{
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": "orchestrator",
                    "action": "gather_data",
                    "data_sources": [],
                    "output_summary": "Database not available - using mock mode",
                }],
                "reasoning": ["Data Moat not available, using mock responses"],
            }
        
        # Gather data based on task type
        if task_type == TaskType.PATIENT_REVIEW.value:
            # Extract patient ID from query
            import re
            patient_match = re.search(r'patient[-_]?(\d+)', query.lower())
            if patient_match:
                patient_id = f"patient-{patient_match.group(1).zfill(3)}"
                result = await self.data_tools.get_patient_summary(patient_id)
                data_queries.append({
                    "tool": "get_patient_summary",
                    "params": {"patient_id": patient_id},
                    "result_summary": f"Found patient with {result.get('condition_count', 0)} conditions",
                })
                tool_results.append({"type": "patient_data", "data": result})
                activities.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": "orchestrator",
                    "action": "query_patient_summary",
                    "data_sources": result.get("data_sources", []),
                    "output_summary": f"Retrieved data for {patient_id}",
                })
            
            # Also get high-risk patients for context
            high_risk = await self.data_tools.get_high_risk_patients(limit=5)
            tool_results.append({"type": "high_risk_patients", "data": high_risk})
            activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "orchestrator",
                "action": "query_high_risk_patients",
                "data_sources": high_risk.get("data_sources", []),
                "output_summary": f"Found {high_risk.get('total_found', 0)} high-risk patients",
            })
        
        elif task_type == TaskType.DENIAL_MANAGEMENT.value:
            # Get denial intelligence
            denial_intel = await self.data_tools.get_denial_intelligence()
            data_queries.append({
                "tool": "get_denial_intelligence",
                "params": {},
                "result_summary": f"Found {denial_intel.get('summary', {}).get('total_denials', 0)} denials",
            })
            tool_results.append({"type": "denial_intelligence", "data": denial_intel})
            activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "orchestrator",
                "action": "query_denial_intelligence",
                "data_sources": denial_intel.get("data_sources", []),
                "output_summary": f"Analyzed {denial_intel.get('summary', {}).get('total_denials', 0)} denials totaling ${denial_intel.get('summary', {}).get('total_denied_amount', 0):,.0f}",
            })
        
        elif task_type == TaskType.CLINICAL_TRIAGE.value:
            # Get patients needing attention
            attention = await self.data_tools.get_patients_needing_attention()
            tool_results.append({"type": "triage_alerts", "data": attention})
            activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "orchestrator",
                "action": "query_clinical_alerts",
                "data_sources": attention.get("data_sources", []),
                "output_summary": f"Found {attention.get('total_alerts', 0)} patients needing attention",
            })
            
            # Also get high-risk patients
            high_risk = await self.data_tools.get_high_risk_patients(limit=10)
            tool_results.append({"type": "high_risk_patients", "data": high_risk})
            activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "orchestrator",
                "action": "query_high_risk_patients",
                "data_sources": high_risk.get("data_sources", []),
                "output_summary": f"Identified {high_risk.get('total_found', 0)} high-risk patients",
            })
        
        return {
            "tool_results": tool_results,
            "data_moat_queries": data_queries,
            "agent_activities": activities,
            "reasoning": [f"Gathered {len(tool_results)} data sets from Data Moat"],
        }
    
    async def _analyze(self, state: OrchestratorState) -> dict:
        """Analyze the gathered data."""
        tool_results = state.get("tool_results", [])
        task_type = state.get("task_type")
        insights = []
        
        for result in tool_results:
            data_type = result.get("type")
            data = result.get("data", {})
            
            if data_type == "patient_data" and "patient" in data:
                patient = data["patient"]
                conditions = data.get("conditions", [])
                meds = data.get("medications", [])
                
                insights.append(f"Patient {patient.get('name')} ({patient.get('mrn')}) is {patient.get('age')} years old")
                if conditions:
                    condition_names = [c.get("display", c.get("code")) for c in conditions[:3]]
                    insights.append(f"Active conditions: {', '.join(condition_names)}")
                if len(meds) >= 5:
                    insights.append(f"⚠️ Polypharmacy alert: {len(meds)} active medications")
            
            elif data_type == "denial_intelligence":
                summary = data.get("summary", {})
                if summary:
                    insights.append(f"Total denied amount: ${summary.get('total_denied_amount', 0):,.0f}")
                    insights.append(f"Pending appeals: {summary.get('pending_appeals', 0)}")
                    if summary.get("urgent_deadlines", 0) > 0:
                        insights.append(f"🚨 {summary['urgent_deadlines']} appeals have urgent deadlines")
                
                urgent = data.get("urgent_denials", [])
                if urgent:
                    top = urgent[0]
                    insights.append(f"Highest value denial: ${top.get('amount', 0):,.0f} ({top.get('denial_reason', 'Unknown')})")
            
            elif data_type == "high_risk_patients":
                patients = data.get("high_risk_patients", [])
                if patients:
                    top = patients[0]
                    insights.append(f"Highest risk patient: {top.get('name')} (score: {top.get('risk_score', 0)})")
                    if top.get("risk_factors"):
                        insights.append(f"Risk factors: {', '.join(top['risk_factors'][:3])}")
            
            elif data_type == "triage_alerts":
                labs = data.get("patients_with_abnormal_labs", [])
                vitals = data.get("patients_with_concerning_vitals", [])
                
                if labs:
                    critical = [l for l in labs if l.get("priority") == "critical"]
                    if critical:
                        insights.append(f"🚨 {len(critical)} patients with critical lab values")
                
                if vitals:
                    insights.append(f"⚠️ {len(vitals)} patients with concerning vitals")
        
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "orchestrator",
            "action": "analyze_data",
            "data_sources": [],
            "output_summary": f"Generated {len(insights)} insights",
        }
        
        return {
            "aggregated_insights": insights,
            "agent_activities": [activity],
            "reasoning": [f"Analysis complete with {len(insights)} findings"],
        }
    
    async def _coordinate_agents(self, state: OrchestratorState) -> dict:
        """Coordinate with sub-agents if needed."""
        task_type = state.get("task_type")
        activities = []
        
        if task_type == TaskType.DENIAL_MANAGEMENT.value:
            # Would invoke ActionAgent here for appeal generation
            activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "action_agent",
                "action": "generate_appeal_recommendations",
                "data_sources": ["postgresql"],
                "output_summary": "Generated prioritized appeal recommendations",
            })
        
        return {
            "sub_agents_called": ["action_agent"] if activities else [],
            "agent_activities": activities,
            "reasoning": ["Coordinated with specialized agents"],
        }
    
    async def _synthesize(self, state: OrchestratorState) -> dict:
        """Synthesize all findings into a coherent response."""
        insights = state.get("aggregated_insights", [])
        task_type = state.get("task_type")
        tool_results = state.get("tool_results", [])
        
        # Build structured response
        synthesis = []
        
        if task_type == TaskType.PATIENT_REVIEW.value:
            synthesis.append("## Patient Review Summary")
        elif task_type == TaskType.DENIAL_MANAGEMENT.value:
            synthesis.append("## Denial Management Intelligence")
        elif task_type == TaskType.CLINICAL_TRIAGE.value:
            synthesis.append("## Clinical Triage Report")
        else:
            synthesis.append("## Analysis Summary")
        
        synthesis.append("\n### Key Findings:")
        for insight in insights:
            synthesis.append(f"- {insight}")
        
        # Add data source attribution
        all_sources = set()
        for result in tool_results:
            sources = result.get("data", {}).get("data_sources", [])
            all_sources.update(sources)
        
        if all_sources:
            synthesis.append(f"\n### Data Sources Used:")
            synthesis.append(f"- {', '.join(all_sources)}")
        
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "orchestrator",
            "action": "synthesize_response",
            "data_sources": list(all_sources),
            "output_summary": "Synthesized findings into response",
        }
        
        return {
            "final_answer": "\n".join(synthesis),
            "agent_activities": [activity],
            "reasoning": ["Synthesized all findings"],
        }
    
    async def _respond(self, state: OrchestratorState) -> dict:
        """Format final response."""
        return {
            "confidence": 0.9,
        }
    
    async def run(self, query: str, user_id: str | None = None) -> dict:
        """
        Run the orchestrator on a query.
        
        Args:
            query: User's request
            user_id: Optional user ID for context
            
        Returns:
            Response with answer, activities, and data sources used
        """
        initial_state: OrchestratorState = {
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
            "task_type": None,
            "sub_agents_called": [],
            "agent_activities": [],
            "data_moat_queries": [],
            "aggregated_insights": [],
        }
        
        try:
            graph = self._build_graph()
            compiled = graph.compile()
            
            final_state = None
            async for state in compiled.astream(initial_state):
                final_state = state
            
            # Extract final values from nested state
            if final_state:
                # LangGraph returns nested state with node names
                all_activities = []
                all_insights = []
                final_answer = None
                confidence = 0.0
                task_type = None
                
                for node_name, node_state in final_state.items():
                    if isinstance(node_state, dict):
                        all_activities.extend(node_state.get("agent_activities", []))
                        all_insights.extend(node_state.get("aggregated_insights", []))
                        if node_state.get("final_answer"):
                            final_answer = node_state["final_answer"]
                        if node_state.get("confidence"):
                            confidence = node_state["confidence"]
                        if node_state.get("task_type"):
                            task_type = node_state["task_type"]
                
                return {
                    "answer": final_answer or "Analysis complete",
                    "task_type": task_type,
                    "activities": all_activities,
                    "insights": all_insights,
                    "confidence": confidence,
                }
            
            return {"answer": "Unable to process request", "activities": []}
            
        except Exception as e:
            logger.error("Orchestrator run failed", error=str(e))
            return {
                "answer": f"Error: {str(e)}",
                "activities": [{
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": "orchestrator",
                    "action": "error",
                    "output_summary": str(e),
                }],
            }
