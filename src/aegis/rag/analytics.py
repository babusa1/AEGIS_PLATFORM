"""
AEGIS RAG Query Analytics

Track and analyze RAG query patterns:
- Query logging
- Popular queries
- Performance metrics
- User feedback
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
from collections import Counter
import uuid
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QueryLog:
    """Log entry for a RAG query."""
    id: str
    query: str
    tenant_id: str
    user_id: str | None = None
    results_count: int = 0
    latency_ms: float = 0.0
    search_type: str = "hybrid"
    filters: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feedback_rating: int | None = None  # 1-5
    feedback_comment: str | None = None


@dataclass
class QueryStats:
    """Statistics for a query pattern."""
    query_pattern: str
    count: int
    avg_latency_ms: float
    avg_results: float
    avg_feedback: float | None = None
    last_seen: datetime | None = None


@dataclass
class LatencyStats:
    """Latency statistics."""
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float


@dataclass
class AnalyticsSummary:
    """Summary of RAG analytics."""
    period_start: datetime
    period_end: datetime
    total_queries: int
    unique_users: int
    avg_latency_ms: float
    avg_results_count: float
    feedback_count: int
    avg_feedback_rating: float | None
    top_queries: list[QueryStats]
    latency_stats: LatencyStats


class RAGAnalytics:
    """
    Tracks and analyzes RAG query patterns.
    
    Features:
    - Query logging with metadata
    - Popular query analysis
    - Latency tracking
    - User feedback collection
    - Query suggestions
    """
    
    def __init__(self, max_history: int = 100000):
        """
        Initialize analytics.
        
        Args:
            max_history: Maximum query logs to keep in memory
        """
        self.max_history = max_history
        self._logs: list[QueryLog] = []
        self._feedback: dict[str, dict] = {}  # query_id -> feedback
    
    def log_query(
        self,
        query: str,
        tenant_id: str,
        user_id: str | None = None,
        results_count: int = 0,
        latency_ms: float = 0.0,
        search_type: str = "hybrid",
        filters: dict | None = None,
    ) -> str:
        """
        Log a RAG query.
        
        Args:
            query: The search query
            tenant_id: Tenant ID
            user_id: Optional user ID
            results_count: Number of results returned
            latency_ms: Query latency in milliseconds
            search_type: Type of search (semantic, keyword, hybrid)
            filters: Any filters applied
        
        Returns:
            Query log ID
        """
        log_id = str(uuid.uuid4())
        
        log = QueryLog(
            id=log_id,
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            results_count=results_count,
            latency_ms=latency_ms,
            search_type=search_type,
            filters=filters or {},
        )
        
        self._logs.append(log)
        
        # Trim history if needed
        if len(self._logs) > self.max_history:
            self._logs = self._logs[-self.max_history:]
        
        return log_id
    
    def record_feedback(
        self,
        query_id: str,
        rating: int,
        comment: str | None = None,
    ) -> bool:
        """
        Record user feedback for a query.
        
        Args:
            query_id: Query log ID
            rating: Rating 1-5
            comment: Optional feedback comment
        
        Returns:
            True if feedback was recorded
        """
        # Find and update the log
        for log in self._logs:
            if log.id == query_id:
                log.feedback_rating = max(1, min(5, rating))
                log.feedback_comment = comment
                return True
        
        return False
    
    def get_popular_queries(
        self,
        tenant_id: str | None = None,
        limit: int = 10,
        days: int = 7,
    ) -> list[QueryStats]:
        """
        Get most popular queries.
        
        Args:
            tenant_id: Filter by tenant
            limit: Number of results
            days: Time window in days
        
        Returns:
            List of QueryStats
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Filter logs
        logs = [
            log for log in self._logs
            if log.timestamp >= cutoff
            and (tenant_id is None or log.tenant_id == tenant_id)
        ]
        
        # Group by normalized query
        query_groups: dict[str, list[QueryLog]] = {}
        for log in logs:
            # Normalize query (lowercase, strip)
            normalized = log.query.lower().strip()
            if normalized not in query_groups:
                query_groups[normalized] = []
            query_groups[normalized].append(log)
        
        # Calculate stats
        stats = []
        for pattern, group_logs in query_groups.items():
            avg_latency = sum(l.latency_ms for l in group_logs) / len(group_logs)
            avg_results = sum(l.results_count for l in group_logs) / len(group_logs)
            
            feedback_logs = [l for l in group_logs if l.feedback_rating is not None]
            avg_feedback = None
            if feedback_logs:
                avg_feedback = sum(l.feedback_rating for l in feedback_logs) / len(feedback_logs)
            
            stats.append(QueryStats(
                query_pattern=pattern,
                count=len(group_logs),
                avg_latency_ms=avg_latency,
                avg_results=avg_results,
                avg_feedback=avg_feedback,
                last_seen=max(l.timestamp for l in group_logs),
            ))
        
        # Sort by count
        stats.sort(key=lambda x: x.count, reverse=True)
        
        return stats[:limit]
    
    def get_latency_percentiles(
        self,
        tenant_id: str | None = None,
        hours: int = 24,
    ) -> LatencyStats:
        """
        Get latency percentiles.
        
        Args:
            tenant_id: Filter by tenant
            hours: Time window in hours
        
        Returns:
            LatencyStats
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        latencies = [
            log.latency_ms for log in self._logs
            if log.timestamp >= cutoff
            and (tenant_id is None or log.tenant_id == tenant_id)
        ]
        
        if not latencies:
            return LatencyStats(0, 0, 0, 0, 0, 0, 0)
        
        latencies.sort()
        n = len(latencies)
        
        def percentile(p: float) -> float:
            idx = int(n * p / 100)
            return latencies[min(idx, n - 1)]
        
        return LatencyStats(
            p50_ms=percentile(50),
            p90_ms=percentile(90),
            p95_ms=percentile(95),
            p99_ms=percentile(99),
            avg_ms=sum(latencies) / n,
            min_ms=min(latencies),
            max_ms=max(latencies),
        )
    
    def get_query_suggestions(
        self,
        prefix: str,
        tenant_id: str | None = None,
        limit: int = 5,
    ) -> list[str]:
        """
        Get query suggestions based on prefix.
        
        Args:
            prefix: Query prefix to match
            tenant_id: Filter by tenant
            limit: Number of suggestions
        
        Returns:
            List of suggested queries
        """
        prefix_lower = prefix.lower().strip()
        
        # Find matching queries
        matching = Counter()
        for log in self._logs:
            if tenant_id and log.tenant_id != tenant_id:
                continue
            
            query_lower = log.query.lower()
            if query_lower.startswith(prefix_lower):
                matching[log.query] += 1
        
        # Return most common matches
        return [query for query, _ in matching.most_common(limit)]
    
    def get_summary(
        self,
        tenant_id: str | None = None,
        days: int = 7,
    ) -> AnalyticsSummary:
        """
        Get analytics summary.
        
        Args:
            tenant_id: Filter by tenant
            days: Time window in days
        
        Returns:
            AnalyticsSummary
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        now = datetime.now(timezone.utc)
        
        # Filter logs
        logs = [
            log for log in self._logs
            if log.timestamp >= cutoff
            and (tenant_id is None or log.tenant_id == tenant_id)
        ]
        
        if not logs:
            return AnalyticsSummary(
                period_start=cutoff,
                period_end=now,
                total_queries=0,
                unique_users=0,
                avg_latency_ms=0,
                avg_results_count=0,
                feedback_count=0,
                avg_feedback_rating=None,
                top_queries=[],
                latency_stats=LatencyStats(0, 0, 0, 0, 0, 0, 0),
            )
        
        unique_users = len(set(l.user_id for l in logs if l.user_id))
        feedback_logs = [l for l in logs if l.feedback_rating is not None]
        
        return AnalyticsSummary(
            period_start=cutoff,
            period_end=now,
            total_queries=len(logs),
            unique_users=unique_users,
            avg_latency_ms=sum(l.latency_ms for l in logs) / len(logs),
            avg_results_count=sum(l.results_count for l in logs) / len(logs),
            feedback_count=len(feedback_logs),
            avg_feedback_rating=(
                sum(l.feedback_rating for l in feedback_logs) / len(feedback_logs)
                if feedback_logs else None
            ),
            top_queries=self.get_popular_queries(tenant_id, limit=10, days=days),
            latency_stats=self.get_latency_percentiles(tenant_id, hours=days * 24),
        )
    
    def get_low_performing_queries(
        self,
        tenant_id: str | None = None,
        min_count: int = 3,
        max_avg_rating: float = 3.0,
    ) -> list[QueryStats]:
        """
        Get queries with low user feedback ratings.
        
        Useful for identifying queries that need improvement.
        """
        popular = self.get_popular_queries(tenant_id, limit=100)
        
        return [
            q for q in popular
            if q.count >= min_count
            and q.avg_feedback is not None
            and q.avg_feedback <= max_avg_rating
        ]
    
    def export_logs(
        self,
        tenant_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Export logs for external analysis."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        logs = [
            log for log in self._logs
            if log.timestamp >= cutoff
            and (tenant_id is None or log.tenant_id == tenant_id)
        ]
        
        return [
            {
                "id": log.id,
                "query": log.query,
                "tenant_id": log.tenant_id,
                "user_id": log.user_id,
                "results_count": log.results_count,
                "latency_ms": log.latency_ms,
                "search_type": log.search_type,
                "timestamp": log.timestamp.isoformat(),
                "feedback_rating": log.feedback_rating,
            }
            for log in logs
        ]


# Global instance
_analytics: RAGAnalytics | None = None


def get_analytics() -> RAGAnalytics:
    """Get the global RAG analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = RAGAnalytics()
    return _analytics
