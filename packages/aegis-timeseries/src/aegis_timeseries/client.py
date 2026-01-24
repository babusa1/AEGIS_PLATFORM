"""TimescaleDB Client"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import structlog

from aegis_timeseries.models import Vital, LabResult, WearableMetric, TimeSeriesQuery

logger = structlog.get_logger(__name__)


@dataclass
class TimeSeriesPoint:
    timestamp: datetime
    value: float
    metadata: dict[str, Any] | None = None


class TimeSeriesClient:
    """TimescaleDB client for healthcare time-series data."""
    
    def __init__(self, connection_string: str | None = None):
        self.connection_string = connection_string
        self._pool = None
        self._in_memory: dict[str, list] = {"vitals": [], "labs": [], "wearables": []}
    
    async def connect(self):
        if self.connection_string:
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(self.connection_string)
                await self._create_tables()
            except Exception as e:
                logger.warning("DB connection failed, using in-memory", error=str(e))
    
    async def _create_tables(self):
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS vitals (
                    time TIMESTAMPTZ NOT NULL,
                    patient_id TEXT NOT NULL,
                    vital_type TEXT NOT NULL,
                    value DOUBLE PRECISION,
                    unit TEXT,
                    source TEXT,
                    tenant_id TEXT
                );
                SELECT create_hypertable('vitals', 'time', if_not_exists => TRUE);
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS lab_results (
                    time TIMESTAMPTZ NOT NULL,
                    patient_id TEXT NOT NULL,
                    test_code TEXT NOT NULL,
                    test_name TEXT,
                    value DOUBLE PRECISION,
                    unit TEXT,
                    reference_low DOUBLE PRECISION,
                    reference_high DOUBLE PRECISION,
                    abnormal BOOLEAN,
                    tenant_id TEXT
                );
                SELECT create_hypertable('lab_results', 'time', if_not_exists => TRUE);
            """)
    
    async def insert_vital(self, vital: Vital):
        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO vitals (time, patient_id, vital_type, value, unit, source, tenant_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, vital.timestamp, vital.patient_id, vital.vital_type.value,
                    vital.value, vital.unit, vital.source, vital.tenant_id)
        else:
            self._in_memory["vitals"].append(vital)
    
    async def insert_lab(self, lab: LabResult):
        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO lab_results (time, patient_id, test_code, test_name, value, unit,
                        reference_low, reference_high, abnormal, tenant_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, lab.timestamp, lab.patient_id, lab.test_code, lab.test_name,
                    lab.value, lab.unit, lab.reference_low, lab.reference_high,
                    lab.abnormal, lab.tenant_id)
        else:
            self._in_memory["labs"].append(lab)
    
    async def insert_wearable(self, metric: WearableMetric):
        self._in_memory["wearables"].append(metric)
    
    async def query_vitals(self, query: TimeSeriesQuery) -> list[TimeSeriesPoint]:
        if self._pool:
            return await self._query_db_vitals(query)
        return self._query_memory_vitals(query)
    
    async def _query_db_vitals(self, query: TimeSeriesQuery) -> list[TimeSeriesPoint]:
        sql = "SELECT time, value FROM vitals WHERE patient_id = $1"
        params = [query.patient_id]
        if query.start_time:
            sql += f" AND time >= ${len(params)+1}"
            params.append(query.start_time)
        if query.end_time:
            sql += f" AND time <= ${len(params)+1}"
            params.append(query.end_time)
        if query.metric_types:
            sql += f" AND vital_type = ANY(${len(params)+1})"
            params.append(query.metric_types)
        sql += " ORDER BY time"
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [TimeSeriesPoint(timestamp=r["time"], value=r["value"]) for r in rows]
    
    def _query_memory_vitals(self, query: TimeSeriesQuery) -> list[TimeSeriesPoint]:
        results = []
        for v in self._in_memory["vitals"]:
            if v.patient_id != query.patient_id:
                continue
            if query.start_time and v.timestamp < query.start_time:
                continue
            if query.end_time and v.timestamp > query.end_time:
                continue
            if query.metric_types and v.vital_type.value not in query.metric_types:
                continue
            results.append(TimeSeriesPoint(timestamp=v.timestamp, value=v.value))
        return sorted(results, key=lambda x: x.timestamp)
    
    async def get_latest_vitals(self, patient_id: str) -> dict[str, TimeSeriesPoint]:
        latest = {}
        for v in self._in_memory["vitals"]:
            if v.patient_id == patient_id:
                key = v.vital_type.value
                if key not in latest or v.timestamp > latest[key].timestamp:
                    latest[key] = TimeSeriesPoint(timestamp=v.timestamp, value=v.value)
        return latest
    
    async def aggregate(self, query: TimeSeriesQuery) -> list[dict]:
        """Aggregate time-series data by interval."""
        points = await self.query_vitals(query)
        if not points or not query.interval:
            return [{"timestamp": p.timestamp, "value": p.value} for p in points]
        
        # Simple bucketing
        interval_map = {"1h": timedelta(hours=1), "1d": timedelta(days=1), "1w": timedelta(weeks=1)}
        interval = interval_map.get(query.interval, timedelta(days=1))
        
        buckets: dict[datetime, list[float]] = {}
        for p in points:
            bucket_time = datetime(p.timestamp.year, p.timestamp.month, p.timestamp.day)
            if bucket_time not in buckets:
                buckets[bucket_time] = []
            buckets[bucket_time].append(p.value)
        
        agg_func = {"avg": lambda x: sum(x)/len(x), "min": min, "max": max, "sum": sum}
        func = agg_func.get(query.aggregation or "avg", lambda x: sum(x)/len(x))
        
        return [{"timestamp": ts, "value": func(vals)} for ts, vals in sorted(buckets.items())]
