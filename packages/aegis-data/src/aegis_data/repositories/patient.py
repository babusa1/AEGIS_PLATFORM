"""Patient Repository"""
from datetime import datetime
import structlog
from aegis_data.repositories.base import BaseRepository
from aegis_data.schemas.entities import Patient

logger = structlog.get_logger(__name__)


class PatientRepository(BaseRepository[Patient]):
    VERTEX_LABEL = "Patient"
    
    async def get(self, id: str) -> Patient | None:
        if not self._graph:
            return None
        query = f"g.V().hasLabel('{self.VERTEX_LABEL}').has('id','{id}').has('tenant_id','{self.tenant_id}').valueMap(true)"
        results = await self._graph.query(query)
        return self._map(results[0]) if results else None
    
    async def get_by_mrn(self, mrn: str) -> Patient | None:
        if not self._graph:
            return None
        query = f"g.V().hasLabel('{self.VERTEX_LABEL}').has('mrn','{mrn}').has('tenant_id','{self.tenant_id}').valueMap(true)"
        results = await self._graph.query(query)
        return self._map(results[0]) if results else None
    
    async def list(self, limit: int = 100, offset: int = 0, **filters) -> list[Patient]:
        if not self._graph:
            return []
        query = self._build_graph_query(self.VERTEX_LABEL, **filters)
        query += f".range({offset},{offset+limit}).valueMap(true)"
        results = await self._graph.query(query)
        return [self._map(r) for r in results]
    
    async def create(self, patient: Patient) -> str:
        if not self._graph:
            raise RuntimeError("No graph")
        patient.tenant_id = self.tenant_id
        patient.created_at = datetime.utcnow()
        await self._graph.add_vertex(self.VERTEX_LABEL, patient.id, patient.model_dump())
        return patient.id
    
    async def update(self, id: str, data: dict) -> bool:
        if not self._graph:
            return False
        data["updated_at"] = datetime.utcnow().isoformat()
        await self._graph.update_vertex(self.VERTEX_LABEL, id, data)
        return True
    
    async def delete(self, id: str) -> bool:
        return await self.update(id, {"deleted": True})
    
    async def get_conditions(self, patient_id: str) -> list:
        if not self._graph:
            return []
        query = f"g.V().has('Patient','id','{patient_id}').out('HAS_CONDITION').valueMap(true)"
        return await self._graph.query(query)
    
    async def get_medications(self, patient_id: str) -> list:
        if not self._graph:
            return []
        query = f"g.V().has('Patient','id','{patient_id}').out('TAKES_MEDICATION').valueMap(true)"
        return await self._graph.query(query)
    
    async def get_patient_360(self, patient_id: str) -> dict:
        patient = await self.get(patient_id)
        if not patient:
            return {}
        return {
            "patient": patient.model_dump(),
            "conditions": await self.get_conditions(patient_id),
            "medications": await self.get_medications(patient_id),
        }
    
    def _map(self, data: dict) -> Patient:
        cleaned = {k: v[0] if isinstance(v, list) and v else v for k, v in data.items()}
        return Patient(**cleaned)
