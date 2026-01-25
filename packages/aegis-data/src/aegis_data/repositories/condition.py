"""Condition Repository"""
from datetime import datetime
from aegis_data.repositories.base import BaseRepository
from aegis_data.schemas.entities import Condition


class ConditionRepository(BaseRepository[Condition]):
    VERTEX_LABEL = "Condition"
    
    async def get(self, id: str) -> Condition | None:
        if not self._graph:
            return None
        query = f"g.V().hasLabel('Condition').has('id','{id}').valueMap(true)"
        results = await self._graph.query(query)
        return self._map(results[0]) if results else None
    
    async def list(self, limit: int = 100, **filters) -> list[Condition]:
        if not self._graph:
            return []
        query = self._build_graph_query(self.VERTEX_LABEL, **filters)
        results = await self._graph.query(query + ".valueMap(true)")
        return [self._map(r) for r in results]
    
    async def create(self, cond: Condition) -> str:
        if not self._graph:
            raise RuntimeError("No graph")
        cond.tenant_id = self.tenant_id
        await self._graph.add_vertex(self.VERTEX_LABEL, cond.id, cond.model_dump())
        return cond.id
    
    async def update(self, id: str, data: dict) -> bool:
        if self._graph:
            await self._graph.update_vertex(self.VERTEX_LABEL, id, data)
        return True
    
    async def delete(self, id: str) -> bool:
        return await self.update(id, {"status": "inactive"})
    
    def _map(self, data: dict) -> Condition:
        cleaned = {k: v[0] if isinstance(v, list) else v for k, v in data.items()}
        return Condition(**cleaned)
