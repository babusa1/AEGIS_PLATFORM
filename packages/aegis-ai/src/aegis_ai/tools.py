"""
Tool Registry

Registry of tools available to AI agents.
Tools enable agents to interact with the graph, APIs, and external systems.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
import json
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Tool:
    """
    A tool that can be called by an agent.
    
    Example:
        @tool
        async def get_patient(patient_id: str) -> dict:
            '''Get patient details by ID.'''
            return await graph.get_vertex("Patient", patient_id)
    """
    
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters
    handler: Callable[..., Awaitable[Any]]
    
    # Metadata
    category: str = "general"
    requires_approval: bool = False
    phi_access: bool = False
    
    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        logger.info(f"Executing tool: {self.name}", args=kwargs)
        try:
            result = await self.handler(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {self.name}", error=str(e))
            raise


class ToolRegistry:
    """
    Registry of available tools.
    
    Agents use this to discover and invoke tools.
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._categories: dict[str, list[str]] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name}", category=tool.category)
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self, category: str | None = None) -> list[Tool]:
        """List all tools, optionally filtered by category."""
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n] for n in names]
        return list(self._tools.values())
    
    def get_schemas(self, tool_names: list[str] | None = None) -> list[dict]:
        """Get OpenAI-format schemas for tools."""
        if tool_names:
            tools = [self._tools[n] for n in tool_names if n in self._tools]
        else:
            tools = list(self._tools.values())
        
        return [t.to_openai_schema() for t in tools]
    
    async def execute(self, name: str, arguments: dict) -> Any:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        
        return await tool.execute(**arguments)


# Global registry
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_default_tools(_registry)
    return _registry


def tool(
    name: str | None = None,
    description: str | None = None,
    category: str = "general",
    requires_approval: bool = False,
    phi_access: bool = False,
):
    """
    Decorator to register a function as a tool.
    
    Example:
        @tool(name="get_patient", category="graph", phi_access=True)
        async def get_patient(patient_id: str) -> dict:
            '''Get patient by ID.'''
            ...
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""
        
        # Build parameter schema from type hints
        import inspect
        sig = inspect.signature(func)
        hints = func.__annotations__
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            param_type = hints.get(param_name, str)
            json_type = _python_type_to_json(param_type)
            
            properties[param_name] = {"type": json_type}
            
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        
        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        
        # Create and register tool
        t = Tool(
            name=tool_name,
            description=tool_desc.strip(),
            parameters=parameters,
            handler=func,
            category=category,
            requires_approval=requires_approval,
            phi_access=phi_access,
        )
        
        get_tool_registry().register(t)
        
        return func
    
    return decorator


def _python_type_to_json(python_type) -> str:
    """Convert Python type to JSON Schema type."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return type_map.get(python_type, "string")


def _register_default_tools(registry: ToolRegistry) -> None:
    """Register default healthcare tools."""
    
    # Graph query tools
    registry.register(Tool(
        name="query_patients",
        description="Search for patients by criteria (name, MRN, DOB)",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Patient name"},
                "mrn": {"type": "string", "description": "Medical record number"},
                "dob": {"type": "string", "description": "Date of birth (YYYY-MM-DD)"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            },
        },
        handler=_placeholder_handler,
        category="graph",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="get_patient_summary",
        description="Get comprehensive patient summary including demographics, conditions, medications",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"},
            },
            "required": ["patient_id"],
        },
        handler=_placeholder_handler,
        category="graph",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="get_encounters",
        description="Get patient encounters/visits",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "type": {"type": "string", "description": "Encounter type (inpatient, outpatient, emergency)"},
            },
            "required": ["patient_id"],
        },
        handler=_placeholder_handler,
        category="graph",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="get_lab_results",
        description="Get patient lab results",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "loinc_code": {"type": "string", "description": "LOINC code for specific test"},
                "days": {"type": "integer", "description": "Look back days", "default": 90},
            },
            "required": ["patient_id"],
        },
        handler=_placeholder_handler,
        category="graph",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="get_medications",
        description="Get patient's current and past medications",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "active_only": {"type": "boolean", "default": True},
            },
            "required": ["patient_id"],
        },
        handler=_placeholder_handler,
        category="graph",
        phi_access=True,
    ))
    
    # Clinical tools
    registry.register(Tool(
        name="calculate_risk_score",
        description="Calculate a clinical risk score (e.g., KFRE, MELD, CHA2DS2-VASc)",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "score_type": {"type": "string", "enum": ["KFRE", "MELD", "CHA2DS2-VASc", "Framingham"]},
            },
            "required": ["patient_id", "score_type"],
        },
        handler=_placeholder_handler,
        category="clinical",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="check_care_gaps",
        description="Check for open care gaps (screenings, vaccinations, etc.)",
        parameters={
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "gap_types": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["patient_id"],
        },
        handler=_placeholder_handler,
        category="clinical",
        phi_access=True,
    ))
    
    # RCM/Financial tools
    registry.register(Tool(
        name="get_claim_status",
        description="Get claim status and denial information",
        parameters={
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "patient_id": {"type": "string"},
            },
        },
        handler=_placeholder_handler,
        category="rcm",
        phi_access=True,
    ))
    
    registry.register(Tool(
        name="draft_appeal_letter",
        description="Draft a denial appeal letter",
        parameters={
            "type": "object",
            "properties": {
                "denial_id": {"type": "string"},
                "supporting_evidence": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["denial_id"],
        },
        handler=_placeholder_handler,
        category="rcm",
        requires_approval=True,
        phi_access=True,
    ))


async def _placeholder_handler(**kwargs) -> dict:
    """Placeholder handler for default tools."""
    return {"status": "not_implemented", "args": kwargs}
