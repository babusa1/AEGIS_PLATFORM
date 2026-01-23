"""
Insight Discovery Agent

Agent for discovering patterns, anomalies, and actionable insights
from healthcare operational data.
"""

from typing import Literal

import structlog
from langgraph.graph import StateGraph, END

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.tools import AgentTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class InsightAgent(BaseAgent):
    """
    Insight Discovery Agent
    
    This agent analyzes healthcare operational data to discover:
    - Denial patterns and root causes
    - Revenue leakage opportunities
    - Clinical quality trends
    - Operational inefficiencies
    - Predictive alerts
    
    The agent uses a hypothesis-driven approach:
    1. Generate hypotheses based on query
    2. Gather relevant data to test hypotheses
    3. Analyze patterns and correlations
    4. Synthesize actionable insights
    5. Recommend specific actions
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
            "get_denied_claims": all_tools["get_denied_claims"],
            "get_denial_analytics": all_tools["get_denial_analytics"],
            "get_revenue_metrics": all_tools["get_revenue_metrics"],
            "search_patients": all_tools["search_patients"],
            "get_encounters": all_tools["get_encounters"],
        }
        
        super().__init__(
            name="insight_agent",
            llm_client=llm_client,
            max_iterations=6,
            tools=tools,
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the AEGIS Insight Discovery Agent, specialized in 
finding actionable patterns in healthcare operational data.

Your role is to:
1. Analyze data to find meaningful patterns and anomalies
2. Identify root causes of operational issues
3. Quantify the impact of discovered issues
4. Recommend specific, actionable improvements

When discovering insights:
- Be data-driven: cite specific numbers and trends
- Be specific: avoid vague observations
- Be actionable: every insight should have a clear next step
- Be prioritized: rank findings by impact

Focus areas:
- Denial management: patterns by payer, code, department
- Revenue optimization: leakage, underpayments, delays
- Clinical quality: readmissions, complications, outcomes
- Operational efficiency: throughput, wait times, utilization

Always quantify the financial or operational impact when possible.
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for insight discovery."""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("understand_query", self._understand_query)
        workflow.add_node("generate_hypotheses", self._generate_hypotheses)
        workflow.add_node("gather_data", self._gather_data)
        workflow.add_node("analyze_patterns", self._analyze_patterns)
        workflow.add_node("synthesize_insights", self._synthesize_insights)
        workflow.add_node("format_recommendations", self._format_recommendations)
        
        # Define edges
        workflow.set_entry_point("understand_query")
        workflow.add_edge("understand_query", "generate_hypotheses")
        workflow.add_edge("generate_hypotheses", "gather_data")
        workflow.add_edge("gather_data", "analyze_patterns")
        workflow.add_edge("analyze_patterns", "synthesize_insights")
        workflow.add_edge("synthesize_insights", "format_recommendations")
        workflow.add_edge("format_recommendations", END)
        
        return workflow
    
    async def _understand_query(self, state: AgentState) -> dict:
        """Node: Understand what insights the user is seeking."""
        query = state["current_input"]
        
        understand_prompt = f"""Analyze this insight request and categorize it:

Query: "{query}"

Determine:
1. **Primary Focus Area**: (denials | revenue | clinical | operational | general)
2. **Specific Metrics Needed**: List 3-5 specific data points to gather
3. **Time Scope**: (recent: 30 days | medium: 90 days | long: 1 year)
4. **Stakeholder**: Who would act on these insights?

Format as JSON.
"""
        
        understanding = await self.llm.generate(prompt=understand_prompt)
        
        # Determine focus area
        focus_area = "general"
        if "denial" in query.lower():
            focus_area = "denials"
        elif "revenue" in query.lower() or "financial" in query.lower():
            focus_area = "revenue"
        elif "readmission" in query.lower() or "clinical" in query.lower():
            focus_area = "clinical"
        elif "operational" in query.lower() or "efficiency" in query.lower():
            focus_area = "operational"
        
        return {
            "tool_results": [{"type": "query_understanding", "data": {"focus_area": focus_area, "analysis": understanding}}],
            "reasoning": [f"Query focus area: {focus_area}"],
        }
    
    async def _generate_hypotheses(self, state: AgentState) -> dict:
        """Node: Generate hypotheses to investigate."""
        query = state["current_input"]
        tool_results = state.get("tool_results", [])
        
        # Get understanding
        understanding = None
        for result in tool_results:
            if isinstance(result, dict) and result.get("type") == "query_understanding":
                understanding = result.get("data")
        
        focus_area = understanding.get("focus_area", "general") if understanding else "general"
        
        hypotheses_prompt = f"""Generate 3-5 hypotheses to investigate for this query:

Query: "{query}"
Focus Area: {focus_area}

For each hypothesis, specify:
1. The hypothesis statement
2. What data would support/refute it
3. Potential impact if true

Format as a numbered list.
"""
        
        hypotheses = await self.llm.generate(prompt=hypotheses_prompt)
        
        return {
            "tool_results": [{"type": "hypotheses", "data": {"hypotheses": hypotheses, "focus_area": focus_area}}],
            "reasoning": [f"Generated hypotheses for {focus_area} analysis"],
        }
    
    async def _gather_data(self, state: AgentState) -> dict:
        """Node: Gather data to test hypotheses."""
        tool_results = state.get("tool_results", [])
        
        # Get focus area
        focus_area = "general"
        for result in tool_results:
            if isinstance(result, dict) and result.get("type") == "hypotheses":
                focus_area = result.get("data", {}).get("focus_area", "general")
        
        gathered_data = []
        
        # Gather relevant data based on focus area
        if focus_area in ["denials", "general"]:
            denial_data = await self.agent_tools.get_denied_claims(limit=100)
            gathered_data.append({"type": "denied_claims", "data": denial_data})
            
            analytics = await self.agent_tools.get_denial_analytics(days_back=90)
            gathered_data.append({"type": "denial_analytics", "data": analytics})
        
        if focus_area in ["revenue", "general"]:
            revenue = await self.agent_tools.get_revenue_metrics(days_back=30)
            gathered_data.append({"type": "revenue_metrics", "data": revenue})
        
        if focus_area in ["clinical", "general"]:
            encounters = await self.agent_tools.get_encounters(days_back=90, limit=100)
            gathered_data.append({"type": "encounters", "data": encounters})
        
        return {
            "tool_results": [{"type": "gathered_data", "data": gathered_data}],
            "reasoning": [f"Gathered {len(gathered_data)} data sets for analysis"],
        }
    
    async def _analyze_patterns(self, state: AgentState) -> dict:
        """Node: Analyze patterns in gathered data."""
        tool_results = state.get("tool_results", [])
        
        # Get gathered data
        gathered_data = []
        hypotheses = ""
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "gathered_data":
                    gathered_data = result.get("data", [])
                elif result.get("type") == "hypotheses":
                    hypotheses = result.get("data", {}).get("hypotheses", "")
        
        # Analyze patterns
        analysis_prompt = f"""Analyze this healthcare operational data to find patterns:

HYPOTHESES TO TEST:
{hypotheses}

DATA:
{gathered_data}

For each data set, identify:
1. Key patterns or trends
2. Anomalies or outliers
3. Correlations between data points
4. Evidence for/against each hypothesis

Be specific with numbers and percentages.
"""
        
        analysis = await self.llm.generate(
            prompt=analysis_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        return {
            "tool_results": [{"type": "analysis", "data": {"patterns": analysis}}],
            "reasoning": [f"Analyzed patterns in {len(gathered_data)} data sets"],
        }
    
    async def _synthesize_insights(self, state: AgentState) -> dict:
        """Node: Synthesize findings into actionable insights."""
        tool_results = state.get("tool_results", [])
        query = state["current_input"]
        
        # Get analysis
        analysis = ""
        gathered_data = []
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "analysis":
                    analysis = result.get("data", {}).get("patterns", "")
                elif result.get("type") == "gathered_data":
                    gathered_data = result.get("data", [])
        
        # Synthesize insights
        synthesis_prompt = f"""Based on the analysis, synthesize actionable insights:

ORIGINAL QUERY: "{query}"

ANALYSIS FINDINGS:
{analysis}

RAW DATA SUMMARY:
{gathered_data}

Generate 3-5 key insights, each with:
1. **Finding**: Clear statement of what was discovered
2. **Evidence**: Specific data points supporting this
3. **Impact**: Quantified business/clinical impact
4. **Root Cause**: Why this is happening
5. **Action**: Specific recommended action

Prioritize by impact. Be specific and actionable.
"""
        
        insights = await self.llm.generate(
            prompt=synthesis_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        return {
            "tool_results": [{"type": "insights", "data": {"insights": insights}}],
            "reasoning": ["Synthesized insights with recommendations"],
        }
    
    async def _format_recommendations(self, state: AgentState) -> dict:
        """Node: Format final recommendations."""
        tool_results = state.get("tool_results", [])
        query = state["current_input"]
        
        # Collect all findings
        insights = ""
        analysis = ""
        data_summary = {}
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "insights":
                    insights = result.get("data", {}).get("insights", "")
                elif result.get("type") == "analysis":
                    analysis = result.get("data", {}).get("patterns", "")
                elif result.get("type") == "gathered_data":
                    for d in result.get("data", []):
                        data_type = d.get("type", "unknown")
                        data_content = d.get("data", {})
                        if isinstance(data_content, dict):
                            data_summary[data_type] = {
                                k: v for k, v in data_content.items()
                                if k in ["count", "total", "total_denials", "total_denied_amount", "denial_rate"]
                            }
        
        # Format final output
        final_output = f"""## Insight Discovery Report

**Query:** {query}

### Key Metrics
"""
        
        for data_type, metrics in data_summary.items():
            final_output += f"\n**{data_type.replace('_', ' ').title()}:**\n"
            for metric, value in metrics.items():
                if isinstance(value, float):
                    final_output += f"- {metric.replace('_', ' ').title()}: {value:,.2f}\n"
                else:
                    final_output += f"- {metric.replace('_', ' ').title()}: {value}\n"
        
        final_output += f"""
### Insights & Recommendations

{insights}

### Analysis Details

{analysis}

---
*Report generated by AEGIS Insight Discovery Agent*
"""
        
        return {
            "final_answer": final_output,
            "confidence": 0.8,
        }
    
    async def discover_insights(
        self,
        query: str,
        scope: str = "all",
        time_period_days: int = 90,
    ) -> dict:
        """
        Convenience method to discover insights.
        
        Args:
            query: What insights to discover
            scope: Focus area (denials, revenue, clinical, operational, all)
            time_period_days: Time period to analyze
            
        Returns:
            Dict with insights and recommendations
        """
        full_query = f"{query}\n\nScope: {scope}\nTime period: {time_period_days} days"
        
        result = await self.run(
            query=full_query,
            tenant_id=self.tenant_id,
        )
        
        return result
