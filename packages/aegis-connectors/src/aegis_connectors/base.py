"""
Base Connector Interface

All data connectors inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import uuid4
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConnectorResult:
    """Result from a connector operation."""
    success: bool
    vertices: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices)
    
    @property
    def edge_count(self) -> int:
        return len(self.edges)


class BaseConnector(ABC):
    """
    Base class for all data connectors.
    
    Connectors parse external data formats and transform
    them into graph vertices and edges.
    """
    
    def __init__(self, tenant_id: str, source_system: str | None = None):
        self.tenant_id = tenant_id
        self.source_system = source_system or self.__class__.__name__
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Type of connector (fhir, hl7v2, x12, etc.)"""
        pass
    
    @abstractmethod
    async def parse(self, data: Any) -> ConnectorResult:
        """
        Parse input data and return vertices/edges.
        
        Args:
            data: Raw input data (string, bytes, dict, etc.)
            
        Returns:
            ConnectorResult with vertices, edges, errors
        """
        pass
    
    @abstractmethod
    async def validate(self, data: Any) -> list[str]:
        """
        Validate input data without parsing.
        
        Returns list of validation errors (empty if valid).
        """
        pass
    
    def _create_vertex(
        self,
        label: str,
        id: str,
        properties: dict[str, Any]
    ) -> dict:
        """Create a vertex dict with common properties."""
        return {
            "label": label,
            "id": id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "created_at": datetime.utcnow().isoformat(),
            **{k: v for k, v in properties.items() if v is not None}
        }
    
    def _create_edge(
        self,
        label: str,
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        properties: dict[str, Any] | None = None
    ) -> dict:
        """Create an edge dict."""
        return {
            "label": label,
            "from_label": from_label,
            "from_id": from_id,
            "to_label": to_label,
            "to_id": to_id,
            "tenant_id": self.tenant_id,
            **(properties or {})
        }
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID."""
        uid = str(uuid4())
        return f"{prefix}{uid}" if prefix else uid
