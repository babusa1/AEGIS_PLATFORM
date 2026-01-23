"""
Ontology Registry

Central registry for all vertex and edge types.
Enables dynamic discovery and validation.
"""

from typing import Type

from aegis_ontology.models.base import BaseVertex, BaseEdge


class VertexRegistry:
    """
    Registry of all vertex types in the ontology.
    
    Usage:
        # Register a vertex type
        VertexRegistry.register(Patient)
        
        # Get vertex class by label
        PatientClass = VertexRegistry.get("Patient")
        
        # List all vertex types
        all_types = VertexRegistry.all()
    """
    
    _registry: dict[str, Type[BaseVertex]] = {}
    
    @classmethod
    def register(cls, vertex_class: Type[BaseVertex]) -> None:
        """Register a vertex type."""
        label = vertex_class.get_label()
        cls._registry[label] = vertex_class
    
    @classmethod
    def get(cls, label: str) -> Type[BaseVertex] | None:
        """Get vertex class by label."""
        return cls._registry.get(label)
    
    @classmethod
    def all(cls) -> dict[str, Type[BaseVertex]]:
        """Get all registered vertex types."""
        return cls._registry.copy()
    
    @classmethod
    def labels(cls) -> list[str]:
        """Get all vertex labels."""
        return list(cls._registry.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear the registry (for testing)."""
        cls._registry.clear()


class EdgeRegistry:
    """
    Registry of all edge types (relationships).
    
    Usage:
        # Register an edge type
        EdgeRegistry.register(HasEncounter)
        
        # Get edge class by label
        EdgeClass = EdgeRegistry.get("HAS_ENCOUNTER")
    """
    
    _registry: dict[str, Type[BaseEdge]] = {}
    
    @classmethod
    def register(cls, edge_class: Type[BaseEdge]) -> None:
        """Register an edge type."""
        label = edge_class.get_label()
        cls._registry[label] = edge_class
    
    @classmethod
    def get(cls, label: str) -> Type[BaseEdge] | None:
        """Get edge class by label."""
        return cls._registry.get(label)
    
    @classmethod
    def all(cls) -> dict[str, Type[BaseEdge]]:
        """Get all registered edge types."""
        return cls._registry.copy()
    
    @classmethod
    def labels(cls) -> list[str]:
        """Get all edge labels."""
        return list(cls._registry.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear the registry."""
        cls._registry.clear()


def register_all_types() -> None:
    """
    Register all ontology types.
    
    Call this at application startup.
    """
    from aegis_ontology.models.base import (
        HasEncounter, HasDiagnosis, HasProcedure, HasObservation,
        HasMedication, TreatedBy, BelongsTo, HasCoverage, HasClaim, HasDenial
    )
    from aegis_ontology.models.clinical import (
        Patient, Provider, Organization, Location,
        Encounter, Diagnosis, Procedure, Observation,
        Medication, AllergyIntolerance
    )
    from aegis_ontology.models.financial import (
        Claim, ClaimLine, Denial, Authorization, Coverage
    )
    
    # Register vertices
    for vertex_class in [
        Patient, Provider, Organization, Location,
        Encounter, Diagnosis, Procedure, Observation,
        Medication, AllergyIntolerance,
        Claim, ClaimLine, Denial, Authorization, Coverage
    ]:
        VertexRegistry.register(vertex_class)
    
    # Register edges
    for edge_class in [
        HasEncounter, HasDiagnosis, HasProcedure, HasObservation,
        HasMedication, TreatedBy, BelongsTo, HasCoverage, HasClaim, HasDenial
    ]:
        EdgeRegistry.register(edge_class)


# Schema validation helpers
def validate_vertex(label: str, properties: dict) -> BaseVertex:
    """
    Validate properties against vertex schema.
    
    Args:
        label: Vertex label
        properties: Property dict
        
    Returns:
        Validated vertex instance
        
    Raises:
        ValueError: If label unknown or validation fails
    """
    vertex_class = VertexRegistry.get(label)
    if vertex_class is None:
        raise ValueError(f"Unknown vertex label: {label}")
    
    return vertex_class.model_validate(properties)


def get_vertex_schema(label: str) -> dict:
    """
    Get JSON schema for a vertex type.
    
    Useful for API documentation and validation.
    """
    vertex_class = VertexRegistry.get(label)
    if vertex_class is None:
        raise ValueError(f"Unknown vertex label: {label}")
    
    return vertex_class.model_json_schema()


def get_fhir_mapping(label: str) -> str | None:
    """Get FHIR resource type for a vertex label."""
    vertex_class = VertexRegistry.get(label)
    if vertex_class:
        return vertex_class.get_fhir_resource_type()
    return None


def get_omop_mapping(label: str) -> str | None:
    """Get OMOP CDM table for a vertex label."""
    vertex_class = VertexRegistry.get(label)
    if vertex_class:
        return vertex_class.get_omop_table()
    return None
