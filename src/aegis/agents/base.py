"""
Base Agent Class

Foundation for all AEGIS agents using LangGraph state management.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypedDict, Annotated, Literal
from enum import Enum
import operator

import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from aegis.bedrock.client import LLMClient, get_llm_client
from aegis.config import get_settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Agent State Definition
# =============================================================================

class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A message in the agent conversation."""
    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    """A tool call made by the agent."""
    id: str
    name: str
    arguments: dict
    result: Any | None = None
    error: str | None = None


class AgentState(TypedDict):
    """
    State for LangGraph agent execution.
    
    This state is passed between nodes in the graph and 
    accumulates information as the agent processes.
    """
    # Core state
    messages: Annotated[list[dict], operator.add]
    current_input: str
    
    # Context
    tenant_id: str
    user_id: str | None
    
    # Tool execution
    tool_calls: Annotated[list[dict], operator.add]
    tool_results: Annotated[list[dict], operator.add]
    
    # Agent reasoning
    reasoning: Annotated[list[str], operator.add]
    plan: list[str]
    
    # Output
    final_answer: str | None
    confidence: float
    
    # Metadata
    iteration: int
    max_iterations: int
    error: str | None


# =============================================================================
# Base Agent Class
# =============================================================================

class BaseAgent(ABC):
    """
    Base class for all AEGIS agents.
    
    Provides:
    - LangGraph state management
    - Tool registration and execution
    - LLM interaction
    - Logging and tracing
    
    Subclasses implement:
    - _build_graph(): Define the agent's workflow graph
    - _get_system_prompt(): Agent-specific system prompt
    """
    
    def __init__(
        self,
        name: str,
        llm_client: LLMClient | None = None,
        max_iterations: int = 10,
        tools: dict | None = None,
    ):
        self.name = name
        self.llm = llm_client or get_llm_client()
        self.max_iterations = max_iterations
        self.tools = tools or {}
        self.memory = MemorySaver()
        
        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile(checkpointer=self.memory)
        
        logger.info(f"Initialized agent: {name}", tools=list(self.tools.keys()))
    
    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for this agent."""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
    
    def register_tool(self, name: str, func: callable, description: str):
        """Register a tool for the agent to use."""
        self.tools[name] = {
            "function": func,
            "description": description,
        }
        logger.debug(f"Registered tool: {name}")
    
    async def _call_llm(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
    ) -> str:
        """Call the LLM with messages."""
        # Convert messages to prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.upper()}: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        
        return await self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt or self._get_system_prompt(),
        )
    
    async def _execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        func = tool["function"]
        
        logger.info(f"Executing tool: {tool_name}", arguments=arguments)
        
        try:
            # Handle both sync and async functions
            import asyncio
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            
            logger.info(f"Tool {tool_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed", error=str(e))
            raise
    
    def _create_initial_state(
        self,
        query: str,
        tenant_id: str,
        user_id: str | None = None,
        context: dict | None = None,
    ) -> AgentState:
        """Create the initial state for agent execution."""
        return AgentState(
            messages=[{"role": "user", "content": query}],
            current_input=query,
            tenant_id=tenant_id,
            user_id=user_id,
            tool_calls=[],
            tool_results=[],
            reasoning=[],
            plan=[],
            final_answer=None,
            confidence=0.0,
            iteration=0,
            max_iterations=self.max_iterations,
            error=None,
        )
    
    async def run(
        self,
        query: str,
        tenant_id: str,
        user_id: str | None = None,
        context: dict | None = None,
        thread_id: str | None = None,
    ) -> dict:
        """
        Run the agent with the given query.
        
        Args:
            query: User query or instruction
            tenant_id: Tenant ID for data scoping
            user_id: Optional user ID
            context: Additional context dict
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Dict with answer, reasoning, confidence, etc.
        """
        import uuid
        thread_id = thread_id or str(uuid.uuid4())
        
        logger.info(
            f"Running agent: {self.name}",
            query=query[:100],
            tenant_id=tenant_id,
            thread_id=thread_id,
        )
        
        initial_state = self._create_initial_state(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            context=context,
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Run the graph
            final_state = await self.compiled_graph.ainvoke(initial_state, config)
            
            return {
                "answer": final_state.get("final_answer"),
                "reasoning": final_state.get("reasoning", []),
                "confidence": final_state.get("confidence", 0.0),
                "tool_calls": final_state.get("tool_calls", []),
                "iterations": final_state.get("iteration", 0),
                "error": final_state.get("error"),
            }
            
        except Exception as e:
            logger.error(f"Agent {self.name} failed", error=str(e))
            return {
                "answer": None,
                "reasoning": [],
                "confidence": 0.0,
                "tool_calls": [],
                "iterations": 0,
                "error": str(e),
            }


# =============================================================================
# Common Agent Nodes
# =============================================================================

async def plan_node(state: AgentState, llm: LLMClient, system_prompt: str) -> dict:
    """
    Planning node - analyzes the query and creates an execution plan.
    """
    query = state["current_input"]
    
    plan_prompt = f"""Analyze this query and create a step-by-step plan:

Query: {query}

Create a numbered list of steps to answer this query.
Consider what data needs to be retrieved and what analysis is needed.
"""
    
    response = await llm.generate(
        prompt=plan_prompt,
        system_prompt=system_prompt,
    )
    
    # Parse plan (simple line-based)
    plan_steps = [
        line.strip() 
        for line in response.split("\n") 
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))
    ]
    
    return {
        "plan": plan_steps,
        "reasoning": [f"Created plan with {len(plan_steps)} steps"],
    }


async def think_node(state: AgentState, llm: LLMClient, system_prompt: str) -> dict:
    """
    Thinking node - reasons about current state and decides next action.
    """
    query = state["current_input"]
    plan = state.get("plan", [])
    tool_results = state.get("tool_results", [])
    iteration = state.get("iteration", 0)
    
    context = f"""
Query: {query}

Plan:
{chr(10).join(plan)}

Tool Results So Far:
{tool_results[-3:] if tool_results else 'None yet'}

Iteration: {iteration + 1}

Based on the plan and results, what should be done next?
If you have enough information to answer, provide the final answer.
Otherwise, specify which tool to call and with what arguments.
"""
    
    response = await llm.generate(
        prompt=context,
        system_prompt=system_prompt,
    )
    
    return {
        "reasoning": [response],
        "iteration": iteration + 1,
    }


async def answer_node(state: AgentState, llm: LLMClient, system_prompt: str) -> dict:
    """
    Answer node - synthesizes final answer from gathered information.
    """
    query = state["current_input"]
    reasoning = state.get("reasoning", [])
    tool_results = state.get("tool_results", [])
    
    synthesis_prompt = f"""
Original Query: {query}

Information Gathered:
{tool_results}

Reasoning Steps:
{reasoning}

Synthesize a clear, complete answer to the original query.
Be specific and cite data where relevant.
"""
    
    response = await llm.generate(
        prompt=synthesis_prompt,
        system_prompt=system_prompt,
    )
    
    return {
        "final_answer": response,
        "confidence": 0.85,  # Would be computed based on evidence quality
    }


def should_continue(state: AgentState) -> Literal["continue", "answer", "error"]:
    """
    Router function - decides whether to continue, answer, or handle error.
    """
    if state.get("error"):
        return "error"
    
    if state.get("iteration", 0) >= state.get("max_iterations", 10):
        return "answer"
    
    if state.get("final_answer"):
        return "answer"
    
    # Check if we have enough information (simplified logic)
    tool_results = state.get("tool_results", [])
    if len(tool_results) >= 2:
        return "answer"
    
    return "continue"
