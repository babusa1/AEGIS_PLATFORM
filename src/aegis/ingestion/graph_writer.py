"""
Graph Writer Service

Writes parsed healthcare data to the JanusGraph/Neptune knowledge graph.
"""

from datetime import date, datetime
from typing import Any
from decimal import Decimal

import structlog

from aegis.models.core import Patient, Provider, Organization
from aegis.models.clinical import Encounter, Diagnosis, Procedure, Observation, Medication
from aegis.models.financial import Claim, Denial, Appeal
from aegis.graph.client import GraphClient

logger = structlog.get_logger(__name__)


class GraphWriter:
    """
    Writes healthcare entities to the graph database.
    
    Handles vertex creation, edge creation, and upsert logic.
    
    Usage:
        async with GraphWriter() as writer:
            patient_id = await writer.write_patient(patient)
            encounter_id = await writer.write_encounter(encounter)
            await writer.create_edge(patient_id, "HAS_ENCOUNTER", encounter_id)
    """
    
    def __init__(self, graph_client: GraphClient | None = None):
        """
        Initialize the graph writer.
        
        Args:
            graph_client: Optional GraphClient instance. If not provided,
                         a new one will be created.
        """
        self._client = graph_client
        self._owns_client = graph_client is None
    
    async def __aenter__(self) -> "GraphWriter":
        if self._owns_client:
            self._client = GraphClient()
            await self._client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_client and self._client:
            await self._client.disconnect()
    
    @property
    def client(self) -> GraphClient:
        if self._client is None:
            raise RuntimeError("GraphWriter not initialized. Use 'async with' or provide a client.")
        return self._client
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert Python values to Gremlin-compatible types."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        return value
    
    def _build_properties(self, model: Any, exclude: set[str] | None = None) -> dict[str, Any]:
        """Extract properties from a Pydantic model for Gremlin."""
        exclude = exclude or set()
        exclude.update({"id", "lines"})  # Always exclude these
        
        props = {}
        for field_name, value in model.model_dump().items():
            if field_name in exclude or value is None:
                continue
            props[field_name] = self._serialize_value(value)
        
        return props
    
    # =========================================================================
    # Vertex Writers
    # =========================================================================
    
    async def write_patient(self, patient: Patient) -> str:
        """
        Write a Patient vertex to the graph.
        
        Uses upsert logic based on (tenant_id, source_system, source_id).
        
        Returns:
            The vertex ID
        """
        props = self._build_properties(patient, exclude={"address", "primary_provider_id"})
        
        # Handle nested address
        if patient.address:
            props["address_line"] = patient.address.line
            props["city"] = patient.address.city
            props["state"] = patient.address.state
            props["postal_code"] = patient.address.postal_code
        
        # Upsert query
        query = """
        g.V()
            .has('Patient', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Patient')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('mrn', mrn)
            .property('given_name', given_name)
            .property('family_name', family_name)
            .property('birth_date', birth_date)
            .property('gender', gender)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Patient vertex", vertex_id=vertex_id, mrn=patient.mrn)
        return vertex_id
    
    async def write_provider(self, provider: Provider) -> str:
        """Write a Provider vertex to the graph."""
        props = self._build_properties(provider, exclude={"organization_id"})
        
        query = """
        g.V()
            .has('Provider', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Provider')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('npi', npi)
            .property('given_name', given_name)
            .property('family_name', family_name)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Provider vertex", vertex_id=vertex_id, npi=provider.npi)
        return vertex_id
    
    async def write_organization(self, org: Organization) -> str:
        """Write an Organization vertex to the graph."""
        props = self._build_properties(org, exclude={"address", "parent_organization_id"})
        
        query = """
        g.V()
            .has('Organization', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Organization')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('name', name)
            .property('type', type)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Organization vertex", vertex_id=vertex_id, name=org.name)
        return vertex_id
    
    async def write_encounter(self, encounter: Encounter) -> str:
        """Write an Encounter vertex to the graph."""
        props = self._build_properties(encounter, exclude={"patient_id", "attending_provider_id", "location_id"})
        
        query = """
        g.V()
            .has('Encounter', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Encounter')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('type', type)
            .property('encounter_class', encounter_class)
            .property('status', status)
            .property('admit_date', admit_date)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Encounter vertex", vertex_id=vertex_id, source_id=encounter.source_id)
        return vertex_id
    
    async def write_diagnosis(self, diagnosis: Diagnosis) -> str:
        """Write a Diagnosis vertex to the graph."""
        props = self._build_properties(diagnosis, exclude={"encounter_id"})
        
        query = """
        g.V()
            .has('Diagnosis', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Diagnosis')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('icd10_code', icd10_code)
            .property('description', description)
            .property('type', type)
            .property('rank', rank)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Diagnosis vertex", vertex_id=vertex_id, icd10=diagnosis.icd10_code)
        return vertex_id
    
    async def write_procedure(self, procedure: Procedure) -> str:
        """Write a Procedure vertex to the graph."""
        props = self._build_properties(procedure, exclude={"encounter_id", "performed_by_id"})
        
        query = """
        g.V()
            .has('Procedure', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Procedure')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('cpt_code', cpt_code)
            .property('description', description)
            .property('procedure_date', procedure_date)
            .property('status', status)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Procedure vertex", vertex_id=vertex_id, cpt=procedure.cpt_code)
        return vertex_id
    
    async def write_observation(self, observation: Observation) -> str:
        """Write an Observation vertex to the graph."""
        props = self._build_properties(observation, exclude={"patient_id", "encounter_id"})
        
        query = """
        g.V()
            .has('Observation', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Observation')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('type', type)
            .property('value', value)
            .property('observation_date', observation_date)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Observation vertex", vertex_id=vertex_id, source_id=observation.source_id)
        return vertex_id
    
    async def write_claim(self, claim: Claim) -> str:
        """Write a Claim vertex to the graph."""
        props = self._build_properties(claim, exclude={"patient_id", "encounter_id", "payer_id", "provider_id", "lines", "secondary_diagnoses"})
        
        query = """
        g.V()
            .has('Claim', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Claim')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('claim_number', claim_number)
            .property('type', type)
            .property('status', status)
            .property('service_date_start', service_date_start)
            .property('billed_amount', billed_amount)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Claim vertex", vertex_id=vertex_id, claim_number=claim.claim_number)
        return vertex_id
    
    async def write_denial(self, denial: Denial) -> str:
        """Write a Denial vertex to the graph."""
        props = self._build_properties(denial, exclude={"claim_id", "payer_id"})
        
        query = """
        g.V()
            .has('Denial', 'tenant_id', tenant_id)
            .has('source_system', source_system)
            .has('source_id', source_id)
            .fold()
            .coalesce(
                unfold(),
                addV('Denial')
                    .property('tenant_id', tenant_id)
                    .property('source_system', source_system)
                    .property('source_id', source_id)
            )
            .property('reason_code', reason_code)
            .property('category', category)
            .property('description', description)
            .property('denied_amount', denied_amount)
            .property('denial_date', denial_date)
            .property('updated_at', updated_at)
            .id()
        """
        
        props["updated_at"] = datetime.now().isoformat()
        
        result = await self.client.execute(query, props)
        vertex_id = result[0] if result else None
        
        logger.debug("Wrote Denial vertex", vertex_id=vertex_id, reason=denial.reason_code)
        return vertex_id
    
    # =========================================================================
    # Edge Writers
    # =========================================================================
    
    async def create_edge(
        self, 
        from_vertex_id: str, 
        edge_label: str, 
        to_vertex_id: str,
        properties: dict[str, Any] | None = None
    ) -> bool:
        """
        Create an edge between two vertices.
        
        Args:
            from_vertex_id: Source vertex ID
            edge_label: Edge label (e.g., "HAS_ENCOUNTER")
            to_vertex_id: Target vertex ID
            properties: Optional edge properties
            
        Returns:
            True if edge was created
        """
        props = properties or {}
        props["created_at"] = datetime.now().isoformat()
        
        query = """
        g.V(from_id)
            .coalesce(
                outE(edge_label).where(inV().hasId(to_id)),
                addE(edge_label).to(V(to_id))
            )
            .property('created_at', created_at)
        """
        
        bindings = {
            "from_id": from_vertex_id,
            "edge_label": edge_label,
            "to_id": to_vertex_id,
            "created_at": props["created_at"],
        }
        
        await self.client.execute(query, bindings)
        
        logger.debug(
            "Created edge",
            from_id=from_vertex_id,
            edge=edge_label,
            to_id=to_vertex_id,
        )
        return True
    
    # =========================================================================
    # Bulk Writers
    # =========================================================================
    
    async def write_fhir_bundle_result(self, parsed_result: dict[str, list]) -> dict[str, int]:
        """
        Write all entities from a parsed FHIR bundle to the graph.
        
        Args:
            parsed_result: Output from FHIRParser.parse_bundle()
            
        Returns:
            Dictionary with counts of written entities
        """
        counts = {
            "patients": 0,
            "providers": 0,
            "organizations": 0,
            "encounters": 0,
            "diagnoses": 0,
            "procedures": 0,
            "observations": 0,
            "claims": 0,
            "edges": 0,
        }
        
        # Maps from source_id to vertex_id
        patient_ids: dict[str, str] = {}
        provider_ids: dict[str, str] = {}
        org_ids: dict[str, str] = {}
        encounter_ids: dict[str, str] = {}
        
        # Write patients
        for patient in parsed_result.get("patients", []):
            vertex_id = await self.write_patient(patient)
            if vertex_id:
                patient_ids[patient.source_id] = vertex_id
                counts["patients"] += 1
        
        # Write providers
        for provider in parsed_result.get("providers", []):
            vertex_id = await self.write_provider(provider)
            if vertex_id:
                provider_ids[provider.source_id] = vertex_id
                counts["providers"] += 1
        
        # Write organizations
        for org in parsed_result.get("organizations", []):
            vertex_id = await self.write_organization(org)
            if vertex_id:
                org_ids[org.source_id] = vertex_id
                counts["organizations"] += 1
        
        # Write encounters and create edges
        for encounter in parsed_result.get("encounters", []):
            vertex_id = await self.write_encounter(encounter)
            if vertex_id:
                encounter_ids[encounter.source_id] = vertex_id
                counts["encounters"] += 1
                
                # Create Patient -> Encounter edge
                if encounter.patient_id in patient_ids:
                    await self.create_edge(
                        patient_ids[encounter.patient_id],
                        "HAS_ENCOUNTER",
                        vertex_id
                    )
                    counts["edges"] += 1
                
                # Create Encounter -> Provider edge
                if encounter.attending_provider_id and encounter.attending_provider_id in provider_ids:
                    await self.create_edge(
                        vertex_id,
                        "ATTENDED_BY",
                        provider_ids[encounter.attending_provider_id]
                    )
                    counts["edges"] += 1
        
        # Write diagnoses
        for diagnosis in parsed_result.get("diagnoses", []):
            vertex_id = await self.write_diagnosis(diagnosis)
            if vertex_id:
                counts["diagnoses"] += 1
                
                # Create Encounter -> Diagnosis edge
                if diagnosis.encounter_id in encounter_ids:
                    await self.create_edge(
                        encounter_ids[diagnosis.encounter_id],
                        "HAS_DIAGNOSIS",
                        vertex_id
                    )
                    counts["edges"] += 1
        
        # Write procedures
        for procedure in parsed_result.get("procedures", []):
            vertex_id = await self.write_procedure(procedure)
            if vertex_id:
                counts["procedures"] += 1
                
                # Create Encounter -> Procedure edge
                if procedure.encounter_id in encounter_ids:
                    await self.create_edge(
                        encounter_ids[procedure.encounter_id],
                        "HAS_PROCEDURE",
                        vertex_id
                    )
                    counts["edges"] += 1
        
        # Write observations
        for observation in parsed_result.get("observations", []):
            vertex_id = await self.write_observation(observation)
            if vertex_id:
                counts["observations"] += 1
                
                # Create Encounter -> Observation edge
                if observation.encounter_id and observation.encounter_id in encounter_ids:
                    await self.create_edge(
                        encounter_ids[observation.encounter_id],
                        "HAS_OBSERVATION",
                        vertex_id
                    )
                    counts["edges"] += 1
        
        # Write claims
        for claim in parsed_result.get("claims", []):
            vertex_id = await self.write_claim(claim)
            if vertex_id:
                counts["claims"] += 1
                
                # Create Encounter -> Claim edge (BILLED_FOR)
                if claim.encounter_id and claim.encounter_id in encounter_ids:
                    await self.create_edge(
                        encounter_ids[claim.encounter_id],
                        "BILLED_FOR",
                        vertex_id
                    )
                    counts["edges"] += 1
        
        logger.info("Wrote FHIR bundle to graph", **counts)
        return counts
