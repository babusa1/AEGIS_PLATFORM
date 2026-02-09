"""
SDK Tool Registry

Tool registration system for SDK agents.
"""

from typing import Dict, Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class SDKToolRegistry:
    """Tool registry for SDK agents."""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, tool_func: Callable, description: str):
        """Register a tool."""
        self.tools[name] = {
            "function": tool_func,
            "description": description,
        }
        logger.info("SDK tool registered", tool_name=name)
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self.tools.get(name, {}).get("function")
