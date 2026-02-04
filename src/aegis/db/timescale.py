"""
AEGIS TimescaleDB Native Queries

TimescaleDB-specific operations for time-series healthcare data:
- Vitals monitoring
- Lab result trends
- Medication schedules
- Patient events timeline
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TimeInterval(str, Enum):
    """Standard time intervals for aggregation."""
    MINUTE_1 = "1 minute"
    MINUTE_5 = "5 minutes"
    MINUTE_15 = "15 minutes"
    HOUR_1 = "1 hour"
    HOUR_4 = "4 hours"
    DAY_1 = "1 day"
    WEEK_1 = "1 week"
    MONTH_1 = "1 month"


class GapFillMethod(str, Enum):
    """Methods for filling gaps in time-series data."""
    INTERPOLATE = "interpolate"  # Linear interpolation
    LOCF = "locf"  # Last observation carried forward
    NULL = "null"  # Leave as NULL


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    timestamp: datetime
    value: float
    metadata: dict[str, Any] | None = None


@dataclass
class AggregatedPoint:
    """An aggregated time series point."""
    bucket: datetime
    avg: float | None = None
    min: float | None = None
    max: float | None = None
    count: int = 0
    sum: float | None = None
    stddev: float | None = None


@dataclass
class VitalSign:
    """A vital sign measurement."""
    patient_id: str
    timestamp: datetime
    vital_type: str  # heart_rate, blood_pressure_systolic, etc.
    value: float
    unit: str
    device_id: str | None = None


class TimescaleDBClient:
    """
    TimescaleDB-specific operations for AEGIS.
    
    Leverages TimescaleDB functions:
    - time_bucket() for aggregation
    - Continuous aggregates for pre-computed rollups
    - Gap filling (interpolate, locf)
    - Compression policies
    """
    
    def __init__(self, pool):
        """
        Initialize with asyncpg connection pool.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
    
    # ==========================================================================
    # Time Bucket Queries
    # ==========================================================================
    
    async def time_bucket_query(
        self,
        table: str,
        time_column: str,
        value_column: str,
        interval: TimeInterval,
        start_time: datetime,
        end_time: datetime,
        patient_id: str | None = None,
        aggregations: list[str] = ["avg", "min", "max", "count"],
    ) -> list[AggregatedPoint]:
        """
        Execute a time_bucket aggregation query.
        
        Args:
            table: Table name (e.g., 'vitals')
            time_column: Name of timestamp column
            value_column: Name of value column to aggregate
            interval: Time bucket interval
            start_time: Query start time
            end_time: Query end time
            patient_id: Optional patient filter
            aggregations: List of aggregations to compute
        
        Returns:
            List of aggregated points
        """
        # Build aggregation expressions
        agg_expressions = []
        for agg in aggregations:
            if agg == "avg":
                agg_expressions.append(f"AVG({value_column}) as avg")
            elif agg == "min":
                agg_expressions.append(f"MIN({value_column}) as min")
            elif agg == "max":
                agg_expressions.append(f"MAX({value_column}) as max")
            elif agg == "count":
                agg_expressions.append(f"COUNT(*) as count")
            elif agg == "sum":
                agg_expressions.append(f"SUM({value_column}) as sum")
            elif agg == "stddev":
                agg_expressions.append(f"STDDEV({value_column}) as stddev")
        
        agg_sql = ", ".join(agg_expressions)
        
        # Build query
        query = f"""
            SELECT 
                time_bucket('{interval.value}', {time_column}) AS bucket,
                {agg_sql}
            FROM {table}
            WHERE {time_column} >= $1 AND {time_column} < $2
        """
        
        params = [start_time, end_time]
        
        if patient_id:
            query += " AND patient_id = $3"
            params.append(patient_id)
        
        query += f" GROUP BY bucket ORDER BY bucket"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    point = AggregatedPoint(bucket=row["bucket"])
                    if "avg" in aggregations:
                        point.avg = float(row["avg"]) if row["avg"] else None
                    if "min" in aggregations:
                        point.min = float(row["min"]) if row["min"] else None
                    if "max" in aggregations:
                        point.max = float(row["max"]) if row["max"] else None
                    if "count" in aggregations:
                        point.count = row["count"]
                    if "sum" in aggregations:
                        point.sum = float(row["sum"]) if row["sum"] else None
                    if "stddev" in aggregations:
                        point.stddev = float(row["stddev"]) if row["stddev"] else None
                    results.append(point)
                
                return results
                
        except Exception as e:
            logger.error("time_bucket_query failed", error=str(e))
            return []
    
    # ==========================================================================
    # Continuous Aggregates
    # ==========================================================================
    
    async def query_continuous_aggregate(
        self,
        aggregate_name: str,
        start_time: datetime,
        end_time: datetime,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query a pre-computed continuous aggregate.
        
        Args:
            aggregate_name: Name of the continuous aggregate view
            start_time: Query start time
            end_time: Query end time
            filters: Additional filter conditions
        
        Returns:
            List of aggregate rows
        """
        query = f"""
            SELECT * FROM {aggregate_name}
            WHERE bucket >= $1 AND bucket < $2
        """
        params = [start_time, end_time]
        
        if filters:
            for i, (key, value) in enumerate(filters.items(), start=3):
                query += f" AND {key} = ${i}"
                params.append(value)
        
        query += " ORDER BY bucket"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("query_continuous_aggregate failed", error=str(e))
            return []
    
    async def create_continuous_aggregate(
        self,
        view_name: str,
        source_table: str,
        time_column: str,
        interval: TimeInterval,
        aggregations: dict[str, str],  # {column: aggregation}
        group_by: list[str] | None = None,
    ) -> bool:
        """
        Create a continuous aggregate view.
        
        Args:
            view_name: Name for the new view
            source_table: Source hypertable
            time_column: Time column name
            interval: Aggregation interval
            aggregations: Dict of column -> aggregation type
            group_by: Additional group by columns
        
        Returns:
            True if successful
        """
        # Build aggregation expressions
        agg_exprs = [f"time_bucket('{interval.value}', {time_column}) AS bucket"]
        
        for column, agg_type in aggregations.items():
            if agg_type == "avg":
                agg_exprs.append(f"AVG({column}) AS avg_{column}")
            elif agg_type == "min":
                agg_exprs.append(f"MIN({column}) AS min_{column}")
            elif agg_type == "max":
                agg_exprs.append(f"MAX({column}) AS max_{column}")
            elif agg_type == "count":
                agg_exprs.append(f"COUNT({column}) AS count_{column}")
            elif agg_type == "sum":
                agg_exprs.append(f"SUM({column}) AS sum_{column}")
        
        if group_by:
            agg_exprs.extend(group_by)
        
        group_clause = "bucket"
        if group_by:
            group_clause += ", " + ", ".join(group_by)
        
        query = f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
            WITH (timescaledb.continuous) AS
            SELECT {', '.join(agg_exprs)}
            FROM {source_table}
            GROUP BY {group_clause}
            WITH NO DATA;
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query)
                logger.info(f"Created continuous aggregate: {view_name}")
                return True
        except Exception as e:
            logger.error("create_continuous_aggregate failed", error=str(e))
            return False
    
    async def refresh_continuous_aggregate(
        self,
        view_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        """Manually refresh a continuous aggregate for a time range."""
        query = f"""
            CALL refresh_continuous_aggregate('{view_name}', $1, $2);
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, start_time, end_time)
                return True
        except Exception as e:
            logger.error("refresh_continuous_aggregate failed", error=str(e))
            return False
    
    # ==========================================================================
    # Gap Filling
    # ==========================================================================
    
    async def gap_fill_query(
        self,
        table: str,
        time_column: str,
        value_column: str,
        interval: TimeInterval,
        start_time: datetime,
        end_time: datetime,
        fill_method: GapFillMethod = GapFillMethod.INTERPOLATE,
        patient_id: str | None = None,
    ) -> list[TimeSeriesPoint]:
        """
        Query time-series data with gap filling.
        
        Args:
            table: Table name
            time_column: Time column name
            value_column: Value column name
            interval: Time bucket interval
            start_time: Query start time
            end_time: Query end time
            fill_method: How to fill gaps
            patient_id: Optional patient filter
        
        Returns:
            List of time series points with gaps filled
        """
        # Build fill expression based on method
        if fill_method == GapFillMethod.INTERPOLATE:
            fill_expr = f"interpolate(AVG({value_column}))"
        elif fill_method == GapFillMethod.LOCF:
            fill_expr = f"locf(AVG({value_column}))"
        else:
            fill_expr = f"AVG({value_column})"
        
        query = f"""
            SELECT 
                time_bucket_gapfill('{interval.value}', {time_column}) AS bucket,
                {fill_expr} AS value
            FROM {table}
            WHERE {time_column} >= $1 AND {time_column} < $2
        """
        
        params = [start_time, end_time]
        
        if patient_id:
            query += " AND patient_id = $3"
            params.append(patient_id)
        
        query += " GROUP BY bucket ORDER BY bucket"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                return [
                    TimeSeriesPoint(
                        timestamp=row["bucket"],
                        value=float(row["value"]) if row["value"] else 0.0,
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error("gap_fill_query failed", error=str(e))
            return []
    
    # ==========================================================================
    # Compression Management
    # ==========================================================================
    
    async def enable_compression(
        self,
        table: str,
        segment_by: list[str] | None = None,
        order_by: str | None = None,
        compress_after: str = "7 days",
    ) -> bool:
        """
        Enable compression on a hypertable.
        
        Args:
            table: Hypertable name
            segment_by: Columns to segment by (better compression)
            order_by: Column to order by within segments
            compress_after: Auto-compress chunks older than this
        
        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                # Set compression settings
                settings = []
                if segment_by:
                    settings.append(f"timescaledb.compress_segmentby = '{','.join(segment_by)}'")
                if order_by:
                    settings.append(f"timescaledb.compress_orderby = '{order_by}'")
                
                if settings:
                    alter_query = f"""
                        ALTER TABLE {table} SET ({', '.join(settings)});
                    """
                    await conn.execute(alter_query)
                
                # Enable compression
                await conn.execute(f"ALTER TABLE {table} SET (timescaledb.compress);")
                
                # Add compression policy
                await conn.execute(f"""
                    SELECT add_compression_policy('{table}', INTERVAL '{compress_after}');
                """)
                
                logger.info(f"Enabled compression on {table}")
                return True
                
        except Exception as e:
            logger.error("enable_compression failed", error=str(e))
            return False
    
    async def get_compression_stats(self, table: str) -> dict[str, Any]:
        """Get compression statistics for a hypertable."""
        query = f"""
            SELECT 
                hypertable_name,
                total_chunks,
                compressed_chunks,
                uncompressed_chunks,
                pg_size_pretty(before_compression_total_bytes) as before_size,
                pg_size_pretty(after_compression_total_bytes) as after_size,
                CASE 
                    WHEN before_compression_total_bytes > 0 
                    THEN round((1 - (after_compression_total_bytes::float / before_compression_total_bytes)) * 100, 2)
                    ELSE 0 
                END as compression_ratio_pct
            FROM hypertable_compression_stats('{table}');
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query)
                if row:
                    return dict(row)
                return {}
        except Exception as e:
            logger.error("get_compression_stats failed", error=str(e))
            return {}
    
    # ==========================================================================
    # Chunk Management
    # ==========================================================================
    
    async def list_chunks(
        self,
        table: str,
        older_than: timedelta | None = None,
    ) -> list[dict[str, Any]]:
        """List chunks for a hypertable."""
        query = f"""
            SELECT 
                chunk_name,
                range_start,
                range_end,
                is_compressed,
                pg_size_pretty(chunk_size) as size
            FROM timescaledb_information.chunks
            WHERE hypertable_name = $1
        """
        params = [table]
        
        if older_than:
            query += " AND range_end < NOW() - $2"
            params.append(older_than)
        
        query += " ORDER BY range_start DESC"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("list_chunks failed", error=str(e))
            return []
    
    async def compress_chunk(self, chunk_name: str) -> bool:
        """Manually compress a specific chunk."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"SELECT compress_chunk('{chunk_name}');")
                return True
        except Exception as e:
            logger.error("compress_chunk failed", error=str(e))
            return False
    
    async def drop_chunks(
        self,
        table: str,
        older_than: timedelta,
    ) -> int:
        """Drop chunks older than specified duration."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"""
                    SELECT drop_chunks('{table}', older_than => $1);
                """, older_than)
                
                dropped_count = result if result else 0
                logger.info(f"Dropped {dropped_count} chunks from {table}")
                return dropped_count
        except Exception as e:
            logger.error("drop_chunks failed", error=str(e))
            return 0
    
    # ==========================================================================
    # Vitals-Specific Queries
    # ==========================================================================
    
    async def get_patient_vitals_trend(
        self,
        patient_id: str,
        vital_type: str,
        start_time: datetime,
        end_time: datetime,
        interval: TimeInterval = TimeInterval.HOUR_1,
    ) -> list[AggregatedPoint]:
        """Get aggregated vital sign trend for a patient."""
        return await self.time_bucket_query(
            table="vitals",
            time_column="recorded_at",
            value_column="value",
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            patient_id=patient_id,
            aggregations=["avg", "min", "max"],
        )
    
    async def get_abnormal_vitals(
        self,
        patient_id: str,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Find abnormal vital readings in the last N hours.
        
        Uses predefined thresholds for common vitals.
        """
        query = """
            WITH vital_thresholds AS (
                SELECT 'heart_rate' as vital_type, 60.0 as low, 100.0 as high
                UNION ALL SELECT 'blood_pressure_systolic', 90.0, 140.0
                UNION ALL SELECT 'blood_pressure_diastolic', 60.0, 90.0
                UNION ALL SELECT 'temperature', 97.0, 99.5
                UNION ALL SELECT 'respiratory_rate', 12.0, 20.0
                UNION ALL SELECT 'oxygen_saturation', 95.0, 100.0
            )
            SELECT 
                v.patient_id,
                v.vital_type,
                v.value,
                v.unit,
                v.recorded_at,
                t.low as threshold_low,
                t.high as threshold_high,
                CASE 
                    WHEN v.value < t.low THEN 'LOW'
                    WHEN v.value > t.high THEN 'HIGH'
                END as status
            FROM vitals v
            JOIN vital_thresholds t ON v.vital_type = t.vital_type
            WHERE v.patient_id = $1
              AND v.recorded_at >= NOW() - INTERVAL '%s hours'
              AND (v.value < t.low OR v.value > t.high)
            ORDER BY v.recorded_at DESC;
        """ % hours
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, patient_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("get_abnormal_vitals failed", error=str(e))
            return []
    
    async def get_vitals_summary(
        self,
        patient_id: str,
        hours: int = 24,
    ) -> dict[str, dict[str, float]]:
        """
        Get summary statistics for all vital types.
        
        Returns:
            Dict mapping vital_type to {avg, min, max, latest}
        """
        query = """
            WITH latest_vitals AS (
                SELECT DISTINCT ON (vital_type)
                    vital_type,
                    value as latest_value,
                    recorded_at as latest_time
                FROM vitals
                WHERE patient_id = $1
                  AND recorded_at >= NOW() - INTERVAL '%s hours'
                ORDER BY vital_type, recorded_at DESC
            ),
            vital_stats AS (
                SELECT 
                    vital_type,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as reading_count
                FROM vitals
                WHERE patient_id = $1
                  AND recorded_at >= NOW() - INTERVAL '%s hours'
                GROUP BY vital_type
            )
            SELECT 
                s.vital_type,
                s.avg_value,
                s.min_value,
                s.max_value,
                s.reading_count,
                l.latest_value,
                l.latest_time
            FROM vital_stats s
            LEFT JOIN latest_vitals l ON s.vital_type = l.vital_type;
        """ % (hours, hours)
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, patient_id)
                
                result = {}
                for row in rows:
                    result[row["vital_type"]] = {
                        "avg": float(row["avg_value"]) if row["avg_value"] else None,
                        "min": float(row["min_value"]) if row["min_value"] else None,
                        "max": float(row["max_value"]) if row["max_value"] else None,
                        "latest": float(row["latest_value"]) if row["latest_value"] else None,
                        "count": row["reading_count"],
                        "latest_time": row["latest_time"],
                    }
                
                return result
        except Exception as e:
            logger.error("get_vitals_summary failed", error=str(e))
            return {}
    
    # ==========================================================================
    # Downsampling Queries
    # ==========================================================================
    
    async def downsample_to_interval(
        self,
        table: str,
        time_column: str,
        value_columns: list[str],
        source_interval: TimeInterval,
        target_interval: TimeInterval,
        start_time: datetime,
        end_time: datetime,
        group_by: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Downsample data from finer to coarser interval.
        
        Useful for creating summary views at different granularities.
        """
        value_aggs = ", ".join([
            f"AVG({col}) as avg_{col}, MIN({col}) as min_{col}, MAX({col}) as max_{col}"
            for col in value_columns
        ])
        
        group_clause = "bucket"
        select_extra = ""
        if group_by:
            group_clause += ", " + ", ".join(group_by)
            select_extra = ", " + ", ".join(group_by)
        
        query = f"""
            SELECT 
                time_bucket('{target_interval.value}', bucket) as downsampled_bucket,
                {value_aggs}
                {select_extra}
            FROM (
                SELECT 
                    time_bucket('{source_interval.value}', {time_column}) as bucket,
                    {', '.join(value_columns)}
                    {select_extra}
                FROM {table}
                WHERE {time_column} >= $1 AND {time_column} < $2
            ) sub
            GROUP BY downsampled_bucket {', ' + ', '.join(group_by) if group_by else ''}
            ORDER BY downsampled_bucket;
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, start_time, end_time)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("downsample_to_interval failed", error=str(e))
            return []


# =============================================================================
# Helper Functions
# =============================================================================

def get_timescale_client(pool) -> TimescaleDBClient:
    """Create a TimescaleDB client from a connection pool."""
    return TimescaleDBClient(pool)
