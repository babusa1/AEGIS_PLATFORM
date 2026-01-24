"""LangGraph-style Agent Orchestration"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class NodeType(str, Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    ROUTER = "router"
    HUMAN = "human"


class EdgeType(str, Enum):
    NORMAL = "normal"
    CONDITIONAL = "conditional"


@dataclass
class AgentState:
    """State passed through the agent graph."""
    messages: list[dict] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    patient_id: str | None = None
    tenant_id: str | None = None
    current_node: str = "start"
    history: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
    
    def set_context(self, key: str, value: Any):
        self.context[key] = value


@dataclass
class Node:
    name: str
    node_type: NodeType
    func: Callable[[AgentState], AgentState] | None = None
    description: str = ""


@dataclass
class Edge:
    from_node: str
    to_node: str
    edge_type: EdgeType = EdgeType.NORMAL
    condition: Callable[[AgentState], bool] | None = None


class AgentGraph:
    """LangGraph-style graph for agent orchestration."""
    
    def __init__(self, name: str = "agent_graph"):
        self.name = name
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._compiled = False
        
        # Add start and end nodes
        self.add_node("start", NodeType.START)
        self.add_node("end", NodeType.END)
    
    def add_node(self, name: str, node_type: NodeType, func: Callable | None = None, description: str = ""):
        self.nodes[name] = Node(name, node_type, func, description)
        return self
    
    def add_edge(self, from_node: str, to_node: str):
        self.edges.append(Edge(from_node, to_node, EdgeType.NORMAL))
        return self
    
    def add_conditional_edge(self, from_node: str, condition: Callable[[AgentState], str]):
        """Add conditional edge that routes based on state."""
        # Store condition that returns next node name
        self.edges.append(Edge(from_node, "__conditional__", EdgeType.CONDITIONAL, condition))
        return self
    
    def compile(self):
        """Validate and compile the graph."""
        # Validate all edges reference valid nodes
        for edge in self.edges:
            if edge.from_node not in self.nodes:
                raise ValueError(f"Edge references unknown node: {edge.from_node}")
            if edge.to_node != "__conditional__" and edge.to_node not in self.nodes:
                raise ValueError(f"Edge references unknown node: {edge.to_node}")
        self._compiled = True
        return self
    
    async def run(self, initial_state: AgentState | None = None, max_steps: int = 50) -> AgentState:
        """Execute the graph."""
        if not self._compiled:
            self.compile()
        
        state = initial_state or AgentState()
        state.current_node = "start"
        steps = 0
        
        while state.current_node != "end" and steps < max_steps:
            steps += 1
            current = self.nodes.get(state.current_node)
            
            if not current:
                state.errors.append(f"Unknown node: {state.current_node}")
                break
            
            # Execute node function
            if current.func:
                try:
                    state = await self._execute_node(current, state)
                except Exception as e:
                    logger.error("Node execution failed", node=current.name, error=str(e))
                    state.errors.append(f"Node {current.name} failed: {str(e)}")
                    break
            
            state.history.append(state.current_node)
            
            # Find next node
            next_node = self._get_next_node(state.current_node, state)
            if not next_node:
                break
            state.current_node = next_node
        
        return state
    
    async def _execute_node(self, node: Node, state: AgentState) -> AgentState:
        """Execute a node's function."""
        import asyncio
        if asyncio.iscoroutinefunction(node.func):
            return await node.func(state)
        return node.func(state)
    
    def _get_next_node(self, current: str, state: AgentState) -> str | None:
        """Get the next node based on edges."""
        for edge in self.edges:
            if edge.from_node != current:
                continue
            if edge.edge_type == EdgeType.CONDITIONAL and edge.condition:
                return edge.condition(state)
            elif edge.edge_type == EdgeType.NORMAL:
                return edge.to_node
        return None


def create_clinical_graph() -> AgentGraph:
    """Create a standard clinical agent graph."""
    graph = AgentGraph("clinical_agent")
    
    # Define nodes
    async def gather_context(state: AgentState) -> AgentState:
        state.set_context("gathered", True)
        state.add_message("system", "Context gathered for patient")
        return state
    
    async def analyze(state: AgentState) -> AgentState:
        state.set_context("analyzed", True)
        state.add_message("assistant", "Analysis complete")
        return state
    
    async def generate_response(state: AgentState) -> AgentState:
        state.add_message("assistant", "Response generated based on analysis")
        return state
    
    def route_decision(state: AgentState) -> str:
        if state.context.get("needs_human"):
            return "human_review"
        return "generate_response"
    
    graph.add_node("gather_context", NodeType.AGENT, gather_context, "Gather patient context")
    graph.add_node("analyze", NodeType.AGENT, analyze, "Analyze clinical data")
    graph.add_node("router", NodeType.ROUTER, description="Route based on confidence")
    graph.add_node("human_review", NodeType.HUMAN, description="Human review required")
    graph.add_node("generate_response", NodeType.AGENT, generate_response, "Generate response")
    
    # Define edges
    graph.add_edge("start", "gather_context")
    graph.add_edge("gather_context", "analyze")
    graph.add_edge("analyze", "router")
    graph.add_conditional_edge("router", route_decision)
    graph.add_edge("human_review", "generate_response")
    graph.add_edge("generate_response", "end")
    
    return graph.compile()
