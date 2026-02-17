"""
Data Ingestion Service

High-level service for ingesting healthcare data into VeritOS.
Orchestrates parsing, validation, and graph writing.
"""

import json
from typing import Any

import structlog

from aegis.ingestion.fhir_parser import FHIRParser
from aegis.ingestion.graph_writer import GraphWriter
from aegis.ingestion.synthetic_data import SyntheticDataGenerator
from aegis.graph.client import GraphClient

logger = structlog.get_logger(__name__)


class IngestionService:
    """
    Service for ingesting healthcare data into VeritOS.
    
    Supports multiple data formats:
    - FHIR R4 Bundles
    - Synthetic data generation
    - (Future) HL7v2 messages
    - (Future) EDI 837/835 claims
    
    Usage:
        service = IngestionService(tenant_id="hospital_a")
        
        # Ingest FHIR data
        result = await service.ingest_fhir_bundle(fhir_json)
        
        # Generate and ingest synthetic data
        result = await service.ingest_synthetic_data(num_patients=100)
    """
    
    def __init__(
        self,
        tenant_id: str = "default",
        source_system: str = "unknown",
        graph_client: GraphClient | None = None
    ):
        """
        Initialize the ingestion service.
        
        Args:
            tenant_id: Multi-tenant identifier
            source_system: Name of the source system
            graph_client: Optional GraphClient instance
        """
        self.tenant_id = tenant_id
        self.source_system = source_system
        self._graph_client = graph_client
    
    async def ingest_fhir_bundle(
        self,
        fhir_data: str | dict,
        source_system: str | None = None
    ) -> dict[str, Any]:
        """
        Ingest a FHIR R4 Bundle into the knowledge graph.
        
        Args:
            fhir_data: FHIR Bundle as JSON string or dict
            source_system: Override source system name
            
        Returns:
            Dictionary with ingestion results and counts
        """
        source = source_system or self.source_system
        
        logger.info(
            "Starting FHIR ingestion",
            tenant_id=self.tenant_id,
            source_system=source,
        )
        
        # Parse FHIR data
        parser = FHIRParser(tenant_id=self.tenant_id, source_system=source)
        parsed_result = parser.parse_bundle(fhir_data)
        
        # Write to graph
        async with GraphWriter(self._graph_client) as writer:
            counts = await writer.write_fhir_bundle_result(parsed_result)
        
        result = {
            "status": "success",
            "tenant_id": self.tenant_id,
            "source_system": source,
            "counts": counts,
        }
        
        logger.info("FHIR ingestion complete", **result)
        return result
    
    async def ingest_synthetic_data(
        self,
        num_patients: int = 100,
        encounters_per_patient: tuple[int, int] = (1, 5),
        denial_rate: float = 0.15,
        seed: int | None = None
    ) -> dict[str, Any]:
        """
        Generate and ingest synthetic healthcare data.
        
        Args:
            num_patients: Number of patients to generate
            encounters_per_patient: Range of encounters per patient
            denial_rate: Percentage of claims to deny
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary with generation/ingestion results
        """
        logger.info(
            "Starting synthetic data ingestion",
            tenant_id=self.tenant_id,
            num_patients=num_patients,
            denial_rate=denial_rate,
        )
        
        # Generate synthetic data
        generator = SyntheticDataGenerator(
            tenant_id=self.tenant_id,
            source_system="synthetic",
            seed=seed,
        )
        
        dataset = generator.generate_complete_dataset(
            num_patients=num_patients,
            encounters_per_patient=encounters_per_patient,
            denial_rate=denial_rate,
        )
        
        # Write to graph
        counts = {
            "organizations": 0,
            "providers": 0,
            "payers": 0,
            "patients": 0,
            "encounters": 0,
            "diagnoses": 0,
            "procedures": 0,
            "claims": 0,
            "denials": 0,
            "edges": 0,
        }
        
        async with GraphWriter(self._graph_client) as writer:
            # Reference ID maps
            org_ids = {}
            provider_ids = {}
            patient_ids = {}
            encounter_ids = {}
            claim_ids = {}
            
            # Write organizations
            for org in dataset["organizations"]:
                vertex_id = await writer.write_organization(org)
                if vertex_id:
                    org_ids[org.source_id] = vertex_id
                    counts["organizations"] += 1
            
            # Write providers
            for provider in dataset["providers"]:
                vertex_id = await writer.write_provider(provider)
                if vertex_id:
                    provider_ids[provider.source_id] = vertex_id
                    counts["providers"] += 1
            
            # Write payers (as Organizations with type=payer)
            for payer in dataset["payers"]:
                from aegis.models.core import Organization as OrgModel
                payer_org = OrgModel(
                    tenant_id=payer.tenant_id,
                    source_system=payer.source_system,
                    source_id=payer.source_id,
                    name=payer.name,
                    type="payer",
                )
                vertex_id = await writer.write_organization(payer_org)
                if vertex_id:
                    org_ids[payer.source_id] = vertex_id
                    counts["payers"] += 1
            
            # Write patients
            for patient in dataset["patients"]:
                vertex_id = await writer.write_patient(patient)
                if vertex_id:
                    patient_ids[patient.source_id] = vertex_id
                    counts["patients"] += 1
            
            # Write encounters and edges
            for encounter in dataset["encounters"]:
                vertex_id = await writer.write_encounter(encounter)
                if vertex_id:
                    encounter_ids[encounter.source_id] = vertex_id
                    counts["encounters"] += 1
                    
                    # Patient -> Encounter edge
                    if encounter.patient_id in patient_ids:
                        await writer.create_edge(
                            patient_ids[encounter.patient_id],
                            "HAS_ENCOUNTER",
                            vertex_id
                        )
                        counts["edges"] += 1
                    
                    # Encounter -> Provider edge
                    if encounter.attending_provider_id and encounter.attending_provider_id in provider_ids:
                        await writer.create_edge(
                            vertex_id,
                            "ATTENDED_BY",
                            provider_ids[encounter.attending_provider_id]
                        )
                        counts["edges"] += 1
            
            # Write diagnoses
            for diagnosis in dataset["diagnoses"]:
                vertex_id = await writer.write_diagnosis(diagnosis)
                if vertex_id:
                    counts["diagnoses"] += 1
                    
                    if diagnosis.encounter_id in encounter_ids:
                        await writer.create_edge(
                            encounter_ids[diagnosis.encounter_id],
                            "HAS_DIAGNOSIS",
                            vertex_id
                        )
                        counts["edges"] += 1
            
            # Write procedures
            for procedure in dataset["procedures"]:
                vertex_id = await writer.write_procedure(procedure)
                if vertex_id:
                    counts["procedures"] += 1
                    
                    if procedure.encounter_id in encounter_ids:
                        await writer.create_edge(
                            encounter_ids[procedure.encounter_id],
                            "HAS_PROCEDURE",
                            vertex_id
                        )
                        counts["edges"] += 1
            
            # Write claims
            for claim in dataset["claims"]:
                vertex_id = await writer.write_claim(claim)
                if vertex_id:
                    claim_ids[claim.source_id] = vertex_id
                    counts["claims"] += 1
                    
                    # Encounter -> Claim edge
                    if claim.encounter_id and claim.encounter_id in encounter_ids:
                        await writer.create_edge(
                            encounter_ids[claim.encounter_id],
                            "BILLED_FOR",
                            vertex_id
                        )
                        counts["edges"] += 1
                    
                    # Claim -> Payer edge
                    if claim.payer_id and claim.payer_id in org_ids:
                        await writer.create_edge(
                            vertex_id,
                            "SUBMITTED_TO",
                            org_ids[claim.payer_id]
                        )
                        counts["edges"] += 1
            
            # Write denials
            for denial in dataset["denials"]:
                vertex_id = await writer.write_denial(denial)
                if vertex_id:
                    counts["denials"] += 1
                    
                    # Claim -> Denial edge
                    if denial.claim_id and denial.claim_id in claim_ids:
                        await writer.create_edge(
                            claim_ids[denial.claim_id],
                            "HAS_DENIAL",
                            vertex_id
                        )
                        counts["edges"] += 1
        
        result = {
            "status": "success",
            "tenant_id": self.tenant_id,
            "counts": counts,
            "summary": {
                "total_patients": counts["patients"],
                "total_encounters": counts["encounters"],
                "total_claims": counts["claims"],
                "total_denials": counts["denials"],
                "denial_rate": counts["denials"] / counts["claims"] if counts["claims"] > 0 else 0,
            }
        }
        
        logger.info("Synthetic data ingestion complete", **result)
        return result
    
    async def get_ingestion_stats(self) -> dict[str, Any]:
        """
        Get statistics about ingested data for this tenant.
        
        Returns:
            Dictionary with counts by entity type
        """
        async with GraphWriter(self._graph_client) as writer:
            query = """
            g.V()
                .has('tenant_id', tenant_id)
                .groupCount()
                .by(label)
            """
            result = await writer.client.execute(query, {"tenant_id": self.tenant_id})
            
            return {
                "tenant_id": self.tenant_id,
                "entity_counts": result[0] if result else {},
            }
