"""
Gremlin Query Patterns for AEGIS

Production-ready graph traversal queries for healthcare data.
"""

from typing import Any
from gremlin_python.process.graph_traversal import GraphTraversalSource, __
from gremlin_python.process.traversal import T, P, Order
import structlog

logger = structlog.get_logger(__name__)


class PatientQueries:
    """Patient-centric graph queries."""
    
    @staticmethod
    async def get_patient_360(
        g: GraphTraversalSource,
        patient_id: str,
        tenant_id: str
    ) -> dict:
        """
        Get comprehensive Patient 360 view.
        
        Returns patient with encounters, conditions, medications, etc.
        """
        result = await (
            g.V()
            .has("Patient", "id", patient_id)
            .has("tenant_id", tenant_id)
            .project(
                "patient",
                "encounters",
                "conditions", 
                "medications",
                "observations",
                "care_gaps",
                "risk_scores"
            )
            .by(__.valueMap(True))
            .by(
                __.out("HAS_ENCOUNTER")
                .order().by("start_date", Order.desc)
                .limit(20)
                .valueMap(True)
                .fold()
            )
            .by(
                __.out("HAS_CONDITION")
                .has("clinical_status", "active")
                .valueMap(True)
                .fold()
            )
            .by(
                __.out("HAS_MEDICATION")
                .has("status", "active")
                .valueMap(True)
                .fold()
            )
            .by(
                __.out("HAS_OBSERVATION")
                .order().by("effective_date", Order.desc)
                .limit(50)
                .valueMap(True)
                .fold()
            )
            .by(
                __.out("HAS_CARE_GAP")
                .has("status", "open")
                .valueMap(True)
                .fold()
            )
            .by(
                __.out("HAS_RISK_SCORE")
                .order().by("calculated_at", Order.desc)
                .limit(5)
                .valueMap(True)
                .fold()
            )
            .next()
        )
        
        return result
    
    @staticmethod
    async def search_patients(
        g: GraphTraversalSource,
        tenant_id: str,
        mrn: str | None = None,
        name: str | None = None,
        birth_date: str | None = None,
        limit: int = 20
    ) -> list[dict]:
        """Search patients by criteria."""
        query = g.V().hasLabel("Patient").has("tenant_id", tenant_id)
        
        if mrn:
            query = query.has("mrn", mrn)
        if name:
            query = query.or_(
                __.has("given_name", P.containing(name)),
                __.has("family_name", P.containing(name))
            )
        if birth_date:
            query = query.has("birth_date", birth_date)
        
        results = await query.limit(limit).valueMap(True).toList()
        return results
    
    @staticmethod
    async def get_patient_timeline(
        g: GraphTraversalSource,
        patient_id: str,
        tenant_id: str,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> list[dict]:
        """Get patient clinical timeline (encounters, conditions, procedures)."""
        query = (
            g.V()
            .has("Patient", "id", patient_id)
            .has("tenant_id", tenant_id)
            .union(
                __.out("HAS_ENCOUNTER").project("type", "data")
                    .by(__.constant("encounter"))
                    .by(__.valueMap(True)),
                __.out("HAS_CONDITION").project("type", "data")
                    .by(__.constant("condition"))
                    .by(__.valueMap(True)),
                __.out("HAS_PROCEDURE").project("type", "data")
                    .by(__.constant("procedure"))
                    .by(__.valueMap(True)),
            )
        )
        
        results = await query.toList()
        return results


class EncounterQueries:
    """Encounter-centric queries."""
    
    @staticmethod
    async def get_encounter_detail(
        g: GraphTraversalSource,
        encounter_id: str,
        tenant_id: str
    ) -> dict:
        """Get detailed encounter with all related data."""
        result = await (
            g.V()
            .has("Encounter", "id", encounter_id)
            .has("tenant_id", tenant_id)
            .project(
                "encounter",
                "patient",
                "diagnoses",
                "procedures",
                "providers",
                "location",
                "observations",
                "claims"
            )
            .by(__.valueMap(True))
            .by(__.in_("HAS_ENCOUNTER").valueMap(True))
            .by(__.out("HAS_DIAGNOSIS").valueMap(True).fold())
            .by(__.out("PERFORMED_PROCEDURE").valueMap(True).fold())
            .by(__.out("WITH_PROVIDER").valueMap(True).fold())
            .by(__.out("AT_LOCATION").valueMap(True).fold())
            .by(__.out("RESULTED_IN").valueMap(True).fold())
            .by(__.in_("FOR_ENCOUNTER").hasLabel("Claim").valueMap(True).fold())
            .next()
        )
        
        return result


class ClaimQueries:
    """Claims and denial queries."""
    
    @staticmethod
    async def get_claim_with_denials(
        g: GraphTraversalSource,
        claim_id: str,
        tenant_id: str
    ) -> dict:
        """Get claim with denial information."""
        result = await (
            g.V()
            .has("Claim", "id", claim_id)
            .has("tenant_id", tenant_id)
            .project(
                "claim",
                "lines",
                "denials",
                "patient",
                "encounter",
                "coverage"
            )
            .by(__.valueMap(True))
            .by(__.out("HAS_LINE").valueMap(True).fold())
            .by(__.out("HAS_DENIAL").valueMap(True).fold())
            .by(__.out("FOR_PATIENT").valueMap(True))
            .by(__.out("FOR_ENCOUNTER").valueMap(True))
            .by(__.out("COVERED_BY").valueMap(True))
            .next()
        )
        
        return result
    
    @staticmethod
    async def get_open_denials(
        g: GraphTraversalSource,
        tenant_id: str,
        limit: int = 100
    ) -> list[dict]:
        """Get all open denials for a tenant."""
        results = await (
            g.V()
            .hasLabel("Denial")
            .has("tenant_id", tenant_id)
            .has("status", "open")
            .order().by("denial_date", Order.desc)
            .limit(limit)
            .project("denial", "claim", "patient")
            .by(__.valueMap(True))
            .by(__.in_("HAS_DENIAL").valueMap(True))
            .by(__.in_("HAS_DENIAL").out("FOR_PATIENT").valueMap(True))
            .toList()
        )
        
        return results


class CareGapQueries:
    """Care gap queries."""
    
    @staticmethod
    async def get_open_gaps_by_patient(
        g: GraphTraversalSource,
        patient_id: str,
        tenant_id: str
    ) -> list[dict]:
        """Get open care gaps for a patient."""
        results = await (
            g.V()
            .has("Patient", "id", patient_id)
            .has("tenant_id", tenant_id)
            .out("HAS_CARE_GAP")
            .has("status", "open")
            .order().by("priority", Order.asc)
            .valueMap(True)
            .toList()
        )
        
        return results
    
    @staticmethod
    async def get_gaps_by_measure(
        g: GraphTraversalSource,
        tenant_id: str,
        measure_id: str,
        limit: int = 100
    ) -> list[dict]:
        """Get all patients with a specific care gap."""
        results = await (
            g.V()
            .hasLabel("CareGap")
            .has("tenant_id", tenant_id)
            .has("measure_id", measure_id)
            .has("status", "open")
            .limit(limit)
            .project("gap", "patient")
            .by(__.valueMap(True))
            .by(__.in_("HAS_CARE_GAP").valueMap(True))
            .toList()
        )
        
        return results


class GraphWriter:
    """Write operations for the graph."""
    
    @staticmethod
    async def create_vertex(
        g: GraphTraversalSource,
        label: str,
        properties: dict[str, Any]
    ) -> str:
        """Create a vertex with properties."""
        query = g.addV(label)
        
        for key, value in properties.items():
            if value is not None:
                query = query.property(key, value)
        
        result = await query.id().next()
        return str(result)
    
    @staticmethod
    async def create_edge(
        g: GraphTraversalSource,
        from_label: str,
        from_id: str,
        edge_label: str,
        to_label: str,
        to_id: str,
        properties: dict[str, Any] | None = None
    ) -> str:
        """Create an edge between vertices."""
        query = (
            g.V().has(from_label, "id", from_id)
            .addE(edge_label)
            .to(__.V().has(to_label, "id", to_id))
        )
        
        if properties:
            for key, value in properties.items():
                if value is not None:
                    query = query.property(key, value)
        
        result = await query.id().next()
        return str(result)
    
    @staticmethod
    async def upsert_vertex(
        g: GraphTraversalSource,
        label: str,
        id_value: str,
        tenant_id: str,
        properties: dict[str, Any]
    ) -> str:
        """Create or update a vertex."""
        query = (
            g.V()
            .has(label, "id", id_value)
            .has("tenant_id", tenant_id)
            .fold()
            .coalesce(
                __.unfold(),
                __.addV(label).property("id", id_value).property("tenant_id", tenant_id)
            )
        )
        
        for key, value in properties.items():
            if value is not None and key not in ("id", "tenant_id"):
                query = query.property(key, value)
        
        result = await query.id().next()
        return str(result)
