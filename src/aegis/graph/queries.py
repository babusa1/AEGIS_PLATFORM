"""
Graph Query Library

Pre-built Gremlin queries for common healthcare graph operations.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from aegis.graph.client import GraphClient

logger = structlog.get_logger(__name__)


@dataclass
class GraphQueries:
    """Collection of common graph queries for healthcare data."""
    
    client: GraphClient
    
    # =========================================================================
    # Patient Queries
    # =========================================================================
    
    async def get_patient_by_mrn(self, mrn: str, tenant_id: str = "default") -> dict | None:
        """
        Get a patient by MRN.
        
        Args:
            mrn: Medical Record Number
            tenant_id: Tenant identifier
            
        Returns:
            Patient vertex properties or None
        """
        query = """
        g.V()
            .has('Patient', 'mrn', mrn)
            .has('tenant_id', tenant_id)
            .valueMap(true)
            .limit(1)
        """
        results = await self.client.execute(
            query,
            {"mrn": mrn, "tenant_id": tenant_id}
        )
        return results[0] if results else None
    
    async def get_patient_by_id(self, patient_id: str) -> dict | None:
        """Get a patient by vertex ID."""
        query = "g.V(patient_id).valueMap(true)"
        results = await self.client.execute(query, {"patient_id": patient_id})
        return results[0] if results else None
    
    async def get_patient_encounters(
        self,
        patient_id: str,
        status: str | None = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Get encounters for a patient.
        
        Args:
            patient_id: Patient vertex ID
            status: Optional filter by encounter status
            limit: Maximum number of encounters
            
        Returns:
            List of encounter vertices
        """
        if status:
            query = """
            g.V(patient_id)
                .out('HAS_ENCOUNTER')
                .has('status', status)
                .order().by('admit_date', desc)
                .limit(limit)
                .valueMap(true)
            """
            bindings = {"patient_id": patient_id, "status": status, "limit": limit}
        else:
            query = """
            g.V(patient_id)
                .out('HAS_ENCOUNTER')
                .order().by('admit_date', desc)
                .limit(limit)
                .valueMap(true)
            """
            bindings = {"patient_id": patient_id, "limit": limit}
        
        return await self.client.execute(query, bindings)
    
    async def get_patient_360_view(self, patient_id: str) -> dict:
        """
        Get a comprehensive 360-degree view of a patient.
        
        Returns patient with all related entities:
        - Encounters
        - Diagnoses
        - Procedures
        - Claims
        - Medications
        
        Args:
            patient_id: Patient vertex ID
            
        Returns:
            Dictionary with patient and all related data
        """
        # Get patient
        patient = await self.get_patient_by_id(patient_id)
        if not patient:
            return {}
        
        # Get encounters with nested data
        encounters_query = """
        g.V(patient_id)
            .out('HAS_ENCOUNTER')
            .project('encounter', 'diagnoses', 'procedures')
            .by(valueMap(true))
            .by(out('HAS_DIAGNOSIS').valueMap(true).fold())
            .by(out('HAS_PROCEDURE').valueMap(true).fold())
        """
        encounters = await self.client.execute(
            encounters_query, 
            {"patient_id": patient_id}
        )
        
        # Get claims
        claims_query = """
        g.V(patient_id)
            .out('HAS_ENCOUNTER')
            .out('BILLED_FOR')
            .project('claim', 'denials')
            .by(valueMap(true))
            .by(out('HAS_DENIAL').valueMap(true).fold())
        """
        claims = await self.client.execute(claims_query, {"patient_id": patient_id})
        
        # Get medications
        medications_query = """
        g.V(patient_id)
            .out('HAS_MEDICATION')
            .valueMap(true)
        """
        medications = await self.client.execute(
            medications_query, 
            {"patient_id": patient_id}
        )
        
        return {
            "patient": patient,
            "encounters": encounters,
            "claims": claims,
            "medications": medications,
        }
    
    # =========================================================================
    # Claim Queries
    # =========================================================================
    
    async def get_claim_by_number(
        self, 
        claim_number: str, 
        tenant_id: str = "default"
    ) -> dict | None:
        """Get a claim by claim number."""
        query = """
        g.V()
            .has('Claim', 'claim_number', claim_number)
            .has('tenant_id', tenant_id)
            .valueMap(true)
            .limit(1)
        """
        results = await self.client.execute(
            query,
            {"claim_number": claim_number, "tenant_id": tenant_id}
        )
        return results[0] if results else None
    
    async def get_claim_with_context(self, claim_id: str) -> dict:
        """
        Get a claim with full context including patient, encounter, and denials.
        
        This is used by the Action Agent for denial appeals.
        """
        query = """
        g.V(claim_id)
            .project('claim', 'patient', 'encounter', 'denials', 'diagnoses', 'procedures')
            .by(valueMap(true))
            .by(in('BILLED_FOR').in('HAS_ENCOUNTER').valueMap(true))
            .by(in('BILLED_FOR').valueMap(true))
            .by(out('HAS_DENIAL').valueMap(true).fold())
            .by(in('BILLED_FOR').out('HAS_DIAGNOSIS').valueMap(true).fold())
            .by(in('BILLED_FOR').out('HAS_PROCEDURE').valueMap(true).fold())
        """
        results = await self.client.execute(query, {"claim_id": claim_id})
        return results[0] if results else {}
    
    async def get_denied_claims(
        self,
        tenant_id: str = "default",
        payer_id: str | None = None,
        min_amount: float | None = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Get denied claims for review/appeal.
        
        Args:
            tenant_id: Tenant identifier
            payer_id: Optional filter by payer
            min_amount: Optional minimum denial amount
            limit: Maximum number of results
            
        Returns:
            List of denied claims with context
        """
        query = """
        g.V()
            .hasLabel('Claim')
            .has('tenant_id', tenant_id)
            .has('status', 'denied')
            .order().by('denied_amount', desc)
            .limit(limit)
            .project('claim', 'patient_mrn', 'denial_reason')
            .by(valueMap(true))
            .by(in('BILLED_FOR').in('HAS_ENCOUNTER').values('mrn'))
            .by(out('HAS_DENIAL').values('reason_code').fold())
        """
        return await self.client.execute(
            query,
            {"tenant_id": tenant_id, "limit": limit}
        )
    
    # =========================================================================
    # Analytics Queries
    # =========================================================================
    
    async def get_denial_summary(self, tenant_id: str = "default") -> dict:
        """
        Get denial analytics summary.
        
        Returns aggregated denial statistics.
        """
        query = """
        g.V()
            .hasLabel('Denial')
            .has('tenant_id', tenant_id)
            .group()
            .by('reason_category')
            .by(
                fold()
                .project('count', 'total_amount')
                .by(count())
                .by(unfold().values('amount').sum())
            )
        """
        return await self.client.execute(query, {"tenant_id": tenant_id})
    
    async def find_similar_appeals(
        self,
        denial_reason_code: str,
        diagnosis_codes: list[str],
        limit: int = 5
    ) -> list[dict]:
        """
        Find similar successful appeals for a given denial.
        
        Used by the Action Agent to find evidence for appeals.
        """
        query = """
        g.V()
            .hasLabel('Appeal')
            .has('status', 'won')
            .where(
                in('APPEALED_WITH')
                .has('reason_code', denial_reason_code)
            )
            .order().by('success_date', desc)
            .limit(limit)
            .project('appeal', 'evidence', 'outcome')
            .by(valueMap(true))
            .by(out('SUPPORTED_BY').valueMap(true).fold())
            .by(values('outcome_notes'))
        """
        return await self.client.execute(
            query,
            {"denial_reason_code": denial_reason_code, "limit": limit}
        )
