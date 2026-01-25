"""Medication Repository"""
from aegis_data.repositories.base import BaseRepository
from aegis_data.schemas.entities import Medication


class MedicationRepository(BaseRepository[Medication]):
    VERTEX_LABEL = "Medication"
    
    async def get(self, id: str) -> Medication | None:
        if not self._graph:
            return None
        results = await self._graph.query(f"g.V().has('id','{id}').valueMap(true)")
        return self._map(results[0]) if results else None
    
    async def list(self, limit: int = 100, **filters) -> list[Medication]:
        if not self._graph:
            return []
        query = self._build_graph_query(self.VERTEX_LABEL, **filters)
        results = await self._graph.query(query + ".valueMap(true)")
        return [self._map(r) for r in results]
    
    async def create(self, med: Medication) -> str:
        if self._graph:
            await self._graph.add_vertex(self.VERTEX_LABEL, med.id, med.model_dump())
        return med.id
    
    async def update(self, id: str, data: dict) -> bool:
        if self._graph:
            await self._graph.update_vertex(self.VERTEX_LABEL, id, data)
        return True
    
    async def delete(self, id: str) -> bool:
        return await self.update(id, {"status": "stopped"})
    
    def _map(self, data: dict) -> Medication:
        return Medication(**{k: v[0] if isinstance(v, list) else v for k, v in data.items()})
