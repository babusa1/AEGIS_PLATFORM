"""
Unified View Agent

Agent for generating comprehensive Patient 360-degree views.
Synthesizes data from multiple sources into a cohesive summary.
"""

from typing import Literal

import structlog
from langgraph.graph import StateGraph, END

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.tools import AgentTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class UnifiedViewAgent(BaseAgent):
    """
    Unified View Agent - Patient 360
    
    This agent synthesizes patient data from multiple sources:
    - Demographics and identifiers
    - Clinical history (encounters, diagnoses, procedures)
    - Medications and allergies
    - Financial data (claims, payments, denials)
    - Risk scores and care gaps
    
    The agent produces a comprehensive, AI-enhanced patient summary
    with actionable insights and recommended next steps.
    """
    
    def __init__(
        self,
        tenant_id: str,
        llm_client: LLMClient | None = None,
    ):
        self.tenant_id = tenant_id
        self.agent_tools = AgentTools(tenant_id)
        
        # Get relevant tools
        all_tools = self.agent_tools.get_all_tools()
        tools = {
            "get_patient": all_tools["get_patient"],
            "get_patient_360": all_tools["get_patient_360"],
            "get_encounters": all_tools["get_encounters"],
            "calculate_risk_score": all_tools["calculate_risk_score"],
        }
        
        super().__init__(
            name="unified_view_agent",
            llm_client=llm_client,
            max_iterations=5,
            tools=tools,
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the AEGIS Unified View Agent, specialized in creating 
comprehensive patient summaries for healthcare operations.

Your role is to:
1. Gather all relevant patient data from the knowledge graph
2. Synthesize the information into a clear, actionable summary
3. Calculate risk scores and identify care gaps
4. Recommend next steps for the care team

Always be precise and cite specific data. Organize information clearly
with sections for demographics, clinical history, financials, and recommendations.

When generating a patient summary:
- Start with key identifiers (name, MRN, DOB)
- Summarize active conditions and recent encounters
- Highlight any red flags or urgent issues
- Include financial summary (outstanding claims, denials)
- End with specific, actionable recommendations
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for unified view generation."""
        
        # Define the workflow
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("gather_data", self._gather_patient_data)
        workflow.add_node("calculate_risks", self._calculate_risks)
        workflow.add_node("synthesize", self._synthesize_summary)
        workflow.add_node("format_output", self._format_output)
        
        # Define edges
        workflow.set_entry_point("gather_data")
        workflow.add_edge("gather_data", "calculate_risks")
        workflow.add_edge("calculate_risks", "synthesize")
        workflow.add_edge("synthesize", "format_output")
        workflow.add_edge("format_output", END)
        
        return workflow
    
    async def _gather_patient_data(self, state: AgentState) -> dict:
        """Node: Gather all patient data from the graph."""
        query = state["current_input"]
        
        # Extract patient identifier from query
        # In production, use NER or structured input
        patient_id = None
        mrn = None
        
        # Simple extraction (would use proper NER in production)
        if "mrn:" in query.lower():
            mrn = query.lower().split("mrn:")[1].split()[0].strip()
        elif "patient_id:" in query.lower():
            patient_id = query.lower().split("patient_id:")[1].split()[0].strip()
        elif "mrn" in query.lower():
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() == "mrn" and i + 1 < len(words):
                    mrn = words[i + 1].strip(".,!?")
                    break
        
        # Get patient data
        if mrn:
            patient_result = await self.agent_tools.get_patient(mrn=mrn)
        elif patient_id:
            patient_result = await self.agent_tools.get_patient(patient_id=patient_id)
        else:
            # Try to extract from the query using LLM
            extract_prompt = f"""Extract the patient identifier from this query:
"{query}"

Return just the MRN or patient ID, nothing else. If none found, return "NONE".
"""
            identifier = await self.llm.generate(prompt=extract_prompt)
            identifier = identifier.strip()
            
            if identifier and identifier != "NONE":
                patient_result = await self.agent_tools.get_patient(mrn=identifier)
            else:
                return {
                    "tool_results": [{"error": "Could not identify patient from query"}],
                    "reasoning": ["Failed to extract patient identifier from query"],
                }
        
        if "error" in patient_result:
            return {
                "tool_results": [patient_result],
                "reasoning": [f"Patient lookup failed: {patient_result.get('error')}"],
            }
        
        # Get 360 view
        patient_data = patient_result.get("patient", {})
        patient_vertex_id = patient_data.get("id", [None])[0] if isinstance(patient_data.get("id"), list) else patient_data.get("id")
        
        if patient_vertex_id:
            full_view = await self.agent_tools.get_patient_360(patient_vertex_id)
        else:
            full_view = {"patient": patient_data}
        
        return {
            "tool_results": [
                {"type": "patient_data", "data": patient_data},
                {"type": "full_360_view", "data": full_view},
            ],
            "reasoning": ["Gathered patient demographics and 360 view"],
        }
    
    async def _calculate_risks(self, state: AgentState) -> dict:
        """Node: Calculate risk scores based on patient data."""
        tool_results = state.get("tool_results", [])
        
        # Extract patient data
        patient_data = None
        full_view = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "patient_data":
                    patient_data = result.get("data")
                elif result.get("type") == "full_360_view":
                    full_view = result.get("data")
        
        if not patient_data:
            return {
                "tool_results": [{"type": "risk_scores", "data": {"error": "No patient data"}}],
                "reasoning": ["Skipped risk calculation - no patient data"],
            }
        
        # Extract data for risk calculation
        birth_date = patient_data.get("birth_date", [""])[0] if isinstance(patient_data.get("birth_date"), list) else patient_data.get("birth_date", "")
        
        # Calculate age (simplified)
        age = 50  # Default
        if birth_date:
            try:
                from datetime import datetime
                birth_year = int(birth_date[:4])
                age = datetime.now().year - birth_year
            except:
                pass
        
        # Count diagnoses and encounters
        diagnoses = full_view.get("diagnoses", []) if full_view else []
        encounters = full_view.get("encounters", []) if full_view else []
        
        diagnosis_codes = [
            d.get("code", [""])[0] if isinstance(d.get("code"), list) else d.get("code", "")
            for d in diagnoses
        ]
        
        recent_admissions = len([e for e in encounters if e.get("type") == "inpatient"])
        chronic_conditions = len([d for d in diagnoses if d.get("status") == "active"])
        
        # Calculate risk
        risk_result = self.agent_tools.calculate_risk_score(
            age=age,
            diagnosis_codes=diagnosis_codes,
            recent_admissions=min(recent_admissions, 5),
            chronic_conditions=min(chronic_conditions, 10),
        )
        
        return {
            "tool_results": [{"type": "risk_scores", "data": risk_result}],
            "reasoning": [f"Calculated risk scores: {risk_result.get('risk_level')} risk"],
        }
    
    async def _synthesize_summary(self, state: AgentState) -> dict:
        """Node: Use LLM to synthesize a patient summary."""
        tool_results = state.get("tool_results", [])
        
        # Collect all data
        patient_data = None
        full_view = None
        risk_scores = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "patient_data":
                    patient_data = result.get("data")
                elif result.get("type") == "full_360_view":
                    full_view = result.get("data")
                elif result.get("type") == "risk_scores":
                    risk_scores = result.get("data")
        
        # Build synthesis prompt
        synthesis_prompt = f"""Create a comprehensive patient summary from this data:

PATIENT DEMOGRAPHICS:
{patient_data}

CLINICAL DATA (360 VIEW):
{full_view}

CALCULATED RISK SCORES:
{risk_scores}

Generate a well-organized summary with these sections:
1. **Patient Overview** - Key identifiers and demographics
2. **Active Conditions** - Current diagnoses and health issues
3. **Recent Clinical Activity** - Last 3 encounters
4. **Medications** - Active prescriptions
5. **Financial Summary** - Claims, denials, outstanding balances
6. **Risk Assessment** - Based on calculated scores
7. **Recommended Actions** - Specific next steps for care team

Be concise but complete. Highlight any urgent issues.
"""
        
        summary = await self.llm.generate(
            prompt=synthesis_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        return {
            "tool_results": [{"type": "ai_summary", "data": summary}],
            "reasoning": ["Synthesized patient summary using LLM"],
        }
    
    async def _format_output(self, state: AgentState) -> dict:
        """Node: Format the final output."""
        tool_results = state.get("tool_results", [])
        
        # Extract components
        patient_data = None
        risk_scores = None
        ai_summary = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "patient_data":
                    patient_data = result.get("data")
                elif result.get("type") == "risk_scores":
                    risk_scores = result.get("data")
                elif result.get("type") == "ai_summary":
                    ai_summary = result.get("data")
        
        # Build final answer
        final_answer = ai_summary or "Unable to generate patient summary."
        
        # Calculate confidence
        confidence = 0.9
        if not patient_data:
            confidence -= 0.3
        if not risk_scores:
            confidence -= 0.1
        if not ai_summary:
            confidence -= 0.3
        
        return {
            "final_answer": final_answer,
            "confidence": max(confidence, 0.1),
        }
    
    async def generate_patient_summary(
        self,
        patient_id: str | None = None,
        mrn: str | None = None,
    ) -> dict:
        """
        Convenience method to generate a patient 360 summary.
        
        Args:
            patient_id: Patient vertex ID
            mrn: Medical Record Number
            
        Returns:
            Dict with summary, risk_scores, and recommendations
        """
        if mrn:
            query = f"Generate a complete 360 view for patient with MRN: {mrn}"
        elif patient_id:
            query = f"Generate a complete 360 view for patient_id: {patient_id}"
        else:
            return {"error": "Either patient_id or mrn must be provided"}
        
        result = await self.run(
            query=query,
            tenant_id=self.tenant_id,
        )
        
        return result
