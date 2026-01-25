"""Encounter Repository"""
from datetime import datetime
from aegis_data.repositories.base import BaseRepository
from aegis_data.schemas.entities import Encounter


class EncounterRepository(BaseRepository[Encounter]):
    VERTEX_LABEL = "Encounter"
    
    async def get(self, id: str) -> Encounter | None:
        if not self._graph:
            return None
        query = f"g.V().hasLabel('{self.VERTEX_LABEL}').has('id','{id}').valueMap(true)"
        results = await self._graph.query(query)
        return self._map(results[0]) if results else None
    
    async def list(self, limit: int = 100, offset: int = 0, **filters) -> list[Encounter]:
        if not self._graph:
            return []
        query = self._build_graph_query(self.VERTEX_LABEL, **filters)
        query += f".order().by('start_date',desc).range({offset},{offset+limit}).valueMap(true)"
        results = await self._graph.query(query)
        return [self._map(r) for r in results]
    
    async def list_by_patient(self, patient_id: str) -> list[Encounter]:
        return await self.list(patient_id=patient_id)
    
    async def create(self, enc: Encounter) -> str:
        if not self._graph:
            raise RuntimeError("No graph")
        enc.tenant_id = self.tenant_id
        enc.created_at = datetime.utcnow()
        await self._graph.add_vertex(self.VERTEX_LABEL, enc.id, enc.model_dump())
        await self._graph.add_edge("Patient", enc.patient_id, self.VERTEX_LABEL, enc.id, "HAD_ENCOUNTER")
        return enc.id
    
    async def update(self, id: str, data: dict) -> bool:
        if not self._graph:
            return False
        await self._graph.update_vertex(self.VERTEX_LABEL, id, data)
        return True
    
    async def delete(self, id: str) -> bool:
        return await self.update(id, {"status": "cancelled"})
    
    def _map(self, data: dict) -> Encounter:
        cleaned = {k: v[0] if isinstance(v, list) and v else v for k, v in data.items()}
        return Encounter(**cleaned)
