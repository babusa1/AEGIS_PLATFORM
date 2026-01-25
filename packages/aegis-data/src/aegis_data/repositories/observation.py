"""Observation Repository - Graph + TimeSeries"""
from datetime import datetime, timedelta
import structlog

from aegis_data.repositories.base import BaseRepository
from aegis_data.schemas.entities import Observation
from aegis_data.schemas.graph import VertexType, EdgeType

logger = structlog.get_logger(__name__)


class ObservationRepository(BaseRepository[Observation]):
    """
    Repository for Observation data access.
    
    Uses both Graph DB (for relationships) and TimescaleDB (for time-series queries).
    """
    
    VERTEX_LABEL = VertexType.OBSERVATION.value
    
    # Categories stored in TimescaleDB
    TIMESERIES_CATEGORIES = ["vital-signs", "laboratory"]
    
    async def get(self, id: str) -> Observation | None:
        if not self._graph:
            return None
        query = f"""
            g.V().hasLabel('{self.VERTEX_LABEL}')
                .has('id', '{id}')
                .has('tenant_id', '{self.tenant_id}')
                .valueMap(true)
        """
        results = await self._graph.query(query)
        return self._map(results[0]) if results else None
    
    async def list(self, limit: int = 100, offset: int = 0, **filters) -> list[Observation]:
        if not self._graph:
            return []
        query = self._build_graph_query(self.VERTEX_LABEL, **filters)
        query += f".order().by('effective_date', desc).range({offset}, {offset + limit}).valueMap(true)"
        results = await self._graph.query(query)
        return [self._map(r) for r in results]
    
    async def list_by_patient(self, patient_id: str, category: str | None = None,
                             code: str | None = None, limit: int = 50) -> list[Observation]:
        filters = {"patient_id": patient_id}
        if category:
            filters["category"] = category
        if code:
            filters["code"] = code
        return await self.list(limit=limit, **filters)
    
    async def get_latest(self, patient_id: str, code: str) -> Observation | None:
        """Get most recent observation for a code."""
        results = await self.list_by_patient(patient_id, code=code, limit=1)
        return results[0] if results else None
    
    async def get_vitals(self, patient_id: str, days: int = 7) -> list[Observation]:
        """Get recent vital signs."""
        return await self.list_by_patient(patient_id, category="vital-signs", limit=100)
    
    async def get_labs(self, patient_id: str, days: int = 30) -> list[Observation]:
        """Get recent lab results."""
        return await self.list_by_patient(patient_id, category="laboratory", limit=100)
    
    async def get_trend(self, patient_id: str, code: str, days: int = 30) -> list[dict]:
        """
        Get time-series trend for a specific observation.
        Uses TimescaleDB if available for better performance.
        """
        if self._timeseries:
            # Use TimescaleDB for time-series queries
            return await self._get_trend_timeseries(patient_id, code, days)
        
        # Fallback to graph
        obs_list = await self.list_by_patient(patient_id, code=code, limit=days * 4)
        return [
            {"timestamp": o.effective_date, "value": o.value_numeric, "unit": o.unit}
            for o in obs_list if o.value_numeric is not None
        ]
    
    async def _get_trend_timeseries(self, patient_id: str, code: str, days: int) -> list[dict]:
        """Query TimescaleDB for trends."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        query = {
            "patient_id": patient_id,
            "metric_types": [code],
            "start_time": start,
            "end_time": end
        }
        points = await self._timeseries.query_vitals(query)
        return [{"timestamp": p.timestamp, "value": p.value} for p in points]
    
    async def create(self, obs: Observation) -> str:
        if not self._graph:
            raise RuntimeError("No graph client")
        
        obs.tenant_id = self.tenant_id
        obs.created_at = datetime.utcnow()
        data = obs.model_dump(exclude_none=True)
        
        # Store in graph
        await self._graph.add_vertex(self.VERTEX_LABEL, obs.id, data)
        await self._graph.add_edge(
            VertexType.PATIENT.value, obs.patient_id,
            self.VERTEX_LABEL, obs.id,
            EdgeType.HAS_OBSERVATION.value)
        
        # Also store in TimescaleDB for time-series queries
        if self._timeseries and obs.category in self.TIMESERIES_CATEGORIES:
            await self._store_timeseries(obs)
        
        return obs.id
    
    async def _store_timeseries(self, obs: Observation):
        """Store observation in TimescaleDB."""
        if obs.category == "vital-signs" and obs.value_numeric is not None:
            await self._timeseries.insert_vital({
                "patient_id": obs.patient_id,
                "vital_type": obs.code,
                "value": obs.value_numeric,
                "unit": obs.unit,
                "timestamp": obs.effective_date or datetime.utcnow()
            })
        elif obs.category == "laboratory" and obs.value_numeric is not None:
            await self._timeseries.insert_lab({
                "patient_id": obs.patient_id,
                "test_code": obs.code,
                "value": obs.value_numeric,
                "unit": obs.unit,
                "timestamp": obs.effective_date or datetime.utcnow()
            })
    
    async def update(self, id: str, data: dict) -> bool:
        if not self._graph:
            return False
        await self._graph.update_vertex(self.VERTEX_LABEL, id, data)
        return True
    
    async def delete(self, id: str) -> bool:
        return await self.update(id, {"status": "cancelled"})
    
    def _map(self, data: dict) -> Observation:
        cleaned = {k: v[0] if isinstance(v, list) and v else v for k, v in data.items()}
        return Observation(**cleaned)
