"""
Base Models for AEGIS Ontology

Provides base classes for all graph vertices and edges with:
- Multi-tenant isolation
- FHIR resource mapping
- Graph serialization
- Audit fields
"""

from datetime import datetime
from typing import Any, ClassVar, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class TenantMixin(BaseModel):
    """Mixin for multi-tenant isolation."""
    
    tenant_id: str = Field(
        default="default",
        description="Multi-tenant isolation ID"
    )


class AuditMixin(BaseModel):
    """Mixin for audit fields."""
    
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp"
    )
    created_by: str | None = Field(
        default=None,
        description="User who created the record"
    )
    updated_by: str | None = Field(
        default=None,
        description="User who last updated the record"
    )


class SourceMixin(BaseModel):
    """Mixin for data lineage tracking."""
    
    source_system: str | None = Field(
        default=None,
        description="Origin system (Epic, Cerner, etc.)"
    )
    source_id: str | None = Field(
        default=None,
        description="ID in source system"
    )
    source_updated_at: datetime | None = Field(
        default=None,
        description="Last update time in source system"
    )


class BaseVertex(TenantMixin, AuditMixin, SourceMixin):
    """
    Base class for all graph vertices (nodes).
    
    All entity models (Patient, Encounter, Claim, etc.) inherit from this.
    
    Attributes:
        id: Unique vertex ID (UUID or graph-assigned)
        label: Graph vertex label (auto-set from class name)
        fhir_resource_type: Corresponding FHIR resource type
        omop_table: Corresponding OMOP CDM table
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="allow",  # Allow extra fields for extensibility
    )
    
    # Class-level metadata
    _label: ClassVar[str] = ""
    _fhir_resource_type: ClassVar[str | None] = None
    _omop_table: ClassVar[str | None] = None
    
    # Instance fields
    id: str | None = Field(
        default=None,
        description="Graph vertex ID"
    )
    
    def __init_subclass__(cls, **kwargs):
        """Auto-set label from class name if not specified."""
        super().__init_subclass__(**kwargs)
        if not cls._label:
            cls._label = cls.__name__
    
    @classmethod
    def get_label(cls) -> str:
        """Get the graph vertex label."""
        return cls._label or cls.__name__
    
    @classmethod
    def get_fhir_resource_type(cls) -> str | None:
        """Get the FHIR resource type this maps to."""
        return cls._fhir_resource_type
    
    @classmethod
    def get_omop_table(cls) -> str | None:
        """Get the OMOP CDM table this maps to."""
        return cls._omop_table
    
    def generate_id(self) -> str:
        """Generate a new vertex ID."""
        self.id = str(uuid4())
        return self.id
    
    def to_graph_properties(self) -> dict[str, Any]:
        """
        Convert to graph-compatible properties.
        
        Flattens nested objects and converts types for graph storage.
        """
        props = {}
        
        for field_name, value in self.model_dump(exclude_none=True).items():
            if value is None:
                continue
            
            # Handle nested Pydantic models
            if isinstance(value, BaseModel):
                # Flatten with prefix
                for k, v in value.model_dump(exclude_none=True).items():
                    props[f"{field_name}_{k}"] = self._serialize_value(v)
            elif isinstance(value, (list, dict)):
                # Store as JSON string for complex types
                import json
                props[field_name] = json.dumps(value)
            else:
                props[field_name] = self._serialize_value(value)
        
        return props
    
    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Serialize a value for graph storage."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (int, float, str, bool)):
            return value
        else:
            return str(value)
    
    @classmethod
    def from_graph_properties(cls, properties: dict[str, Any]) -> "BaseVertex":
        """Create instance from graph properties."""
        return cls.model_validate(properties)


class BaseEdge(BaseModel):
    """
    Base class for graph edges (relationships).
    
    Edges connect vertices and can have properties.
    
    Attributes:
        id: Edge ID
        label: Edge label (relationship type)
        from_vertex_id: Source vertex ID
        to_vertex_id: Target vertex ID
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    _label: ClassVar[str] = ""
    
    id: str | None = Field(default=None, description="Edge ID")
    from_vertex_id: str = Field(..., description="Source vertex ID")
    to_vertex_id: str = Field(..., description="Target vertex ID")
    
    # Optional edge properties
    created_at: datetime | None = None
    properties: dict[str, Any] | None = None
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls._label:
            # Convert CamelCase to SCREAMING_SNAKE_CASE
            import re
            name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).upper()
            cls._label = name
    
    @classmethod
    def get_label(cls) -> str:
        """Get edge label."""
        return cls._label or cls.__name__.upper()


# ==================== COMMON EDGE TYPES ====================

class HasEncounter(BaseEdge):
    """Patient -> Encounter relationship."""
    _label = "HAS_ENCOUNTER"


class HasDiagnosis(BaseEdge):
    """Encounter -> Diagnosis relationship."""
    _label = "HAS_DIAGNOSIS"
    rank: int | None = None


class HasProcedure(BaseEdge):
    """Encounter -> Procedure relationship."""
    _label = "HAS_PROCEDURE"


class HasObservation(BaseEdge):
    """Patient/Encounter -> Observation relationship."""
    _label = "HAS_OBSERVATION"


class HasMedication(BaseEdge):
    """Patient -> Medication relationship."""
    _label = "HAS_MEDICATION"


class TreatedBy(BaseEdge):
    """Encounter -> Provider relationship."""
    _label = "TREATED_BY"
    role: str | None = None  # attending, consulting, etc.


class BelongsTo(BaseEdge):
    """Provider -> Organization relationship."""
    _label = "BELONGS_TO"


class HasCoverage(BaseEdge):
    """Patient -> Coverage relationship."""
    _label = "HAS_COVERAGE"


class HasClaim(BaseEdge):
    """Encounter -> Claim relationship."""
    _label = "HAS_CLAIM"


class HasDenial(BaseEdge):
    """Claim -> Denial relationship."""
    _label = "HAS_DENIAL"
