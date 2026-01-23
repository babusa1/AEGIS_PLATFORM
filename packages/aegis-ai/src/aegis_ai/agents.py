"""
Agent Orchestration

LangGraph-style agents for healthcare workflows.
"""

from typing import Any, Callable
from enum import Enum
import json
import structlog

from aegis_ai.models import AgentState, AgentConfig, Message
from aegis_ai.gateway import LLMGateway, get_llm_gateway
from aegis_ai.tools import ToolRegistry, get_tool_registry

logger = structlog.get_logger(__name__)


class AgentStep(str, Enum):
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    END = "end"


class Agent:
    """Healthcare AI Agent with ReAct-style reasoning."""
    
    def __init__(
        self,
        config: AgentConfig,
        gateway: LLMGateway | None = None,
        tools: ToolRegistry | None = None,
    ):
        self.config = config
        self._gateway = gateway
        self._tools = tools
    
    async def _get_gateway(self) -> LLMGateway:
        if self._gateway is None:
            self._gateway = await get_llm_gateway()
        return self._gateway
    
    def _get_tools(self) -> ToolRegistry:
        if self._tools is None:
            self._tools = get_tool_registry()
        return self._tools
    
    async def run(
        self,
        user_input: str,
        context: dict | None = None,
        state: AgentState | None = None,
    ) -> AgentState:
        """Run agent on user input."""
        if state is None:
            state = AgentState(agent_id=self.config.name)
        
        if context:
            state.patient_id = context.get("patient_id")
            state.tenant_id = context.get("tenant_id")
        
        if not state.messages:
            state.messages.append(Message.system(self.config.system_prompt))
        
        state.messages.append(Message.user(user_input))
        
        gateway = await self._get_gateway()
        tools = self._get_tools()
        
        for iteration in range(self.config.max_iterations):
            tool_schemas = tools.get_schemas(self.config.tools) if self.config.tools else None
            
            response = await gateway.complete(
                messages=state.messages,
                model=self.config.model,
                temperature=self.config.temperature,
                tools=tool_schemas,
            )
            
            if response.tool_calls:
                state.messages.append(Message.assistant(response.content or ""))
                
                for tc in response.tool_calls:
                    try:
                        result = await tools.execute(tc.name, tc.arguments)
                        state.messages.append(Message.tool(
                            content=json.dumps(result) if isinstance(result, dict) else str(result),
                            name=tc.name,
                            tool_call_id=tc.id,
                        ))
                    except Exception as e:
                        state.messages.append(Message.tool(
                            content=f"Error: {e}",
                            name=tc.name,
                            tool_call_id=tc.id,
                        ))
            else:
                if response.content:
                    state.messages.append(Message.assistant(response.content))
                break
        
        return state
    
    def get_response(self, state: AgentState) -> str:
        for msg in reversed(state.messages):
            if msg.role.value == "assistant" and msg.content:
                return msg.content
        return ""


# Pre-configured agents
AGENT_CONFIGS = {
    "patient_360": AgentConfig(
        name="patient_360",
        description="Unified patient view",
        system_prompt="You are a healthcare AI that provides patient summaries using available tools.",
        tools=["get_patient_summary", "get_encounters", "get_lab_results", "get_medications"],
    ),
    "care_gap": AgentConfig(
        name="care_gap",
        description="Care gap identification",
        system_prompt="You identify missing preventive care and screenings for patients.",
        tools=["get_patient_summary", "check_care_gaps", "calculate_risk_score"],
    ),
    "denial_writer": AgentConfig(
        name="denial_writer",
        description="Denial appeal writer",
        system_prompt="You draft denial appeal letters with clinical evidence.",
        tools=["get_claim_status", "get_patient_summary", "draft_appeal_letter"],
    ),
}


def get_agent(name: str, **kwargs) -> Agent:
    """Get a pre-configured agent."""
    config = AGENT_CONFIGS.get(name)
    if not config:
        raise ValueError(f"Unknown agent: {name}")
    return Agent(config=config, **kwargs)
