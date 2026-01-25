"""
Unified Data Service - Single interface for all data access.

This is the ONLY interface agents should use for data access.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import structlog

from aegis_data.repositories.patient import PatientRepository
from aegis_data.repositories.condition import ConditionRepository
from aegis_data.repositories.medication import MedicationRepository
from aegis_data.repositories.encounter import EncounterRepository
from aegis_data.repositories.observation import ObservationRepository
from aegis_data.schemas.entities import Patient, Condition, Medication, Encounter, Observation

logger = structlog.get_logger(__name__)


@dataclass
class DataClients:
    """Database client connections."""
    graph: Any = None
    postgres: Any = None
    timeseries: Any = None
    vector: Any = None


class DataService:
    """
    Unified Data Service for AEGIS.
    
    Provides single interface for agents to access all data:
    - Clinical data (Graph DB)
    - Operational metadata (Postgres)
    - Time-series (TimescaleDB)
    - Semantic search (Vector DB)
    
    Usage:
        service = DataService(tenant_id="tenant-1", clients=clients)
        
        # Get patient with all related data
        patient_360 = await service.get_patient_360("patient-123")
        
        # Get vital trends
        bp_trend = await service.get_vital_trend("patient-123", "bp_systolic", days=30)
        
        # Semantic search
        similar = await service.search_similar_patients("65yo male with diabetes")
    """
    
    def __init__(self, tenant_id: str, clients: DataClients | None = None):
        self.tenant_id = tenant_id
        self._clients = clients or DataClients()
        
        # Initialize repositories
        self.patients = PatientRepository(
            tenant_id=tenant_id,
            graph_client=self._clients.graph,
            postgres_client=self._clients.postgres
        )
        self.conditions = ConditionRepository(
            tenant_id=tenant_id,
            graph_client=self._clients.graph
        )
        self.medications = MedicationRepository(
            tenant_id=tenant_id,
            graph_client=self._clients.graph
        )
        self.encounters = EncounterRepository(
            tenant_id=tenant_id,
            graph_client=self._clients.graph
        )
        self.observations = ObservationRepository(
            tenant_id=tenant_id,
            graph_client=self._clients.graph,
            timeseries_client=self._clients.timeseries
        )
    
    # === High-Level Patient Methods ===
    
    async def get_patient_360(self, patient_id: str) -> dict:
        """
        Get complete patient view with all related data.
        
        Returns:
            {
                "patient": {...},
                "conditions": [...],
                "medications": [...],
                "encounters": [...],
                "recent_vitals": {...},
                "summary": {...}
            }
        """
        patient = await self.patients.get(patient_id)
        if not patient:
            return {}
        
        conditions = await self.conditions.list(patient_id=patient_id)
        medications = await self.medications.list(patient_id=patient_id)
        encounters = await self.encounters.list(patient_id=patient_id, limit=10)
        vitals = await self.get_latest_vitals(patient_id)
        
        return {
            "patient": patient.model_dump(),
            "conditions": [c.model_dump() for c in conditions],
            "medications": [m.model_dump() for m in medications],
            "encounters": [e.model_dump() for e in encounters],
            "recent_vitals": vitals,
            "summary": {
                "age": patient.age,
                "active_conditions": len([c for c in conditions if c.status == "active"]),
                "active_medications": len([m for m in medications if m.status == "active"]),
                "recent_encounters": len(encounters),
            }
        }
    
    async def get_patient_summary(self, patient_id: str) -> str:
        """Get natural language patient summary for AI context."""
        data = await self.get_patient_360(patient_id)
        if not data:
            return "Patient not found."
        
        patient = data["patient"]
        summary = data["summary"]
        
        lines = [
            f"Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}",
            f"Age: {summary.get('age', 'Unknown')}",
            f"Gender: {patient.get('gender', 'Unknown')}",
            f"Active Conditions: {summary.get('active_conditions', 0)}",
            f"Active Medications: {summary.get('active_medications', 0)}",
        ]
        
        if data["conditions"]:
            lines.append("\nConditions:")
            for c in data["conditions"][:5]:
                lines.append(f"  - {c.get('display', c.get('code', 'Unknown'))}")
        
        if data["medications"]:
            lines.append("\nMedications:")
            for m in data["medications"][:5]:
                lines.append(f"  - {m.get('display', 'Unknown')} {m.get('dosage', '')}")
        
        return "\n".join(lines)
    
    # === Time-Series Methods ===
    
    async def get_latest_vitals(self, patient_id: str) -> dict[str, Any]:
        """Get most recent value for each vital type."""
        vital_types = ["heart_rate", "bp_systolic", "bp_diastolic", "temperature", "spo2", "weight"]
        latest = {}
        
        for vital_type in vital_types:
            obs = await self.observations.get_latest(patient_id, vital_type)
            if obs:
                latest[vital_type] = {
                    "value": obs.value_numeric,
                    "unit": obs.unit,
                    "timestamp": obs.effective_date.isoformat() if obs.effective_date else None
                }
        
        return latest
    
    async def get_vital_trend(self, patient_id: str, vital_type: str, days: int = 30) -> list[dict]:
        """Get time-series trend for a vital sign."""
        return await self.observations.get_trend(patient_id, vital_type, days)
    
    async def get_lab_history(self, patient_id: str, test_code: str, days: int = 365) -> list[dict]:
        """Get history of a specific lab test."""
        return await self.observations.get_trend(patient_id, test_code, days)
    
    # === Search Methods ===
    
    async def search_patients(self, query: str, limit: int = 20) -> list[Patient]:
        """Search patients by name or MRN."""
        # Simple implementation - production would use full-text search
        all_patients = await self.patients.list(limit=100)
        query_lower = query.lower()
        
        matches = []
        for p in all_patients:
            if (query_lower in p.first_name.lower() or 
                query_lower in p.last_name.lower() or
                (p.mrn and query_lower in p.mrn.lower())):
                matches.append(p)
        
        return matches[:limit]
    
    async def search_similar_patients(self, description: str, limit: int = 5) -> list[dict]:
        """Find patients with similar clinical profiles using vector search."""
        if not self._clients.vector:
            return []
        
        # Use vector store for semantic search
        results = await self._clients.vector.find_similar_patients(
            patient_summary=description,
            tenant_id=self.tenant_id,
            top_k=limit
        )
        return results
    
    async def search_conditions(self, code: str | None = None, display: str | None = None) -> list[Condition]:
        """Search conditions by code or display text."""
        filters = {}
        if code:
            filters["code"] = code
        return await self.conditions.list(**filters)
    
    # === Analytics Methods ===
    
    async def get_patient_risk_factors(self, patient_id: str) -> dict:
        """Get risk factors for a patient."""
        data = await self.get_patient_360(patient_id)
        
        risk_factors = {
            "chronic_conditions": [],
            "high_risk_medications": [],
            "abnormal_vitals": [],
            "risk_score": 0.0
        }
        
        # Check conditions
        high_risk_conditions = ["diabetes", "heart failure", "copd", "ckd"]
        for cond in data.get("conditions", []):
            display = cond.get("display", "").lower()
            if any(hrc in display for hrc in high_risk_conditions):
                risk_factors["chronic_conditions"].append(cond.get("display"))
                risk_factors["risk_score"] += 0.1
        
        # Check vitals
        vitals = data.get("recent_vitals", {})
        if vitals.get("bp_systolic", {}).get("value", 0) > 140:
            risk_factors["abnormal_vitals"].append("High blood pressure")
            risk_factors["risk_score"] += 0.1
        
        return risk_factors
    
    async def get_care_gaps(self, patient_id: str) -> list[dict]:
        """Identify care gaps for a patient."""
        data = await self.get_patient_360(patient_id)
        gaps = []
        
        # Check for diabetes without HbA1c in last 6 months
        has_diabetes = any("diabetes" in c.get("display", "").lower() 
                          for c in data.get("conditions", []))
        if has_diabetes:
            # Would check for recent HbA1c
            gaps.append({
                "type": "lab",
                "description": "HbA1c test may be due",
                "condition": "Diabetes"
            })
        
        return gaps
    
    # === Graph Traversal Methods ===
    
    async def get_patient_network(self, patient_id: str, depth: int = 2) -> dict:
        """Get patient's care network (providers, facilities, etc.)."""
        if not self._clients.graph:
            return {}
        
        # Graph traversal to find related entities
        query = f"""
            g.V().has('Patient', 'id', '{patient_id}')
                .repeat(both().simplePath())
                .times({depth})
                .path()
        """
        paths = await self._clients.graph.query(query)
        return {"patient_id": patient_id, "network_paths": paths}
    
    async def find_related_patients(self, patient_id: str, by: str = "condition") -> list[str]:
        """Find patients with similar conditions."""
        if not self._clients.graph:
            return []
        
        query = f"""
            g.V().has('Patient', 'id', '{patient_id}')
                .out('HAS_CONDITION')
                .in('HAS_CONDITION')
                .dedup()
                .values('id')
        """
        return await self._clients.graph.query(query)
