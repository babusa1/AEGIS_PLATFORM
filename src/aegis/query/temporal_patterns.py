"""
Temporal Pattern Matching Engine

Enables queries like:
- "Patients who showed a 20% drop in eGFR within 3 months of starting SGLT2 inhibitor"
- "Find patients with potassium > 6.0 after ACE inhibitor start"
- "Identify patients with HbA1c improvement > 1% within 6 months"

Uses vectorized timelines with Time_Offset for efficient pattern matching.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

from aegis.digital_twin.timeline import VectorizedTimeline, TimelineEvent

logger = structlog.get_logger(__name__)


@dataclass
class TemporalPattern:
    """
    A temporal pattern to match.
    
    Example: "eGFR drop > 20% within 3 months after SGLT2 start"
    """
    pattern_id: str
    description: str
    
    # Event sequence
    trigger_event_type: str  # e.g., "medication" (SGLT2 start)
    trigger_event_filter: Dict[str, Any]  # e.g., {"code": "SGLT2"}
    
    target_event_type: str  # e.g., "lab" (eGFR)
    target_event_filter: Dict[str, Any]  # e.g., {"code": "eGFR"}
    
    # Temporal constraints
    time_window_months: float  # e.g., 3 months
    time_window_days: Optional[int] = None
    
    # Pattern conditions
    condition: str  # e.g., "drop_percentage > 0.2" or "value_change < -20"
    threshold: float  # e.g., 0.2 (20%) or -20 (absolute)
    
    # Direction
    direction: str = "decrease"  # "increase", "decrease", "any"


class TemporalPatternMatcher:
    """
    Temporal pattern matching engine.
    
    Matches patterns across patient timelines using Time_Offset calculations.
    """
    
    def __init__(self, db_pool=None, graph_client=None):
        """
        Initialize pattern matcher.
        
        Args:
            db_pool: Database connection pool
            graph_client: Graph database client
        """
        self.db_pool = db_pool
        self.graph_client = graph_client
    
    async def find_patients_matching_pattern(
        self,
        pattern: TemporalPattern,
        tenant_id: str,
        patient_ids: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find patients matching a temporal pattern.
        
        Args:
            pattern: Temporal pattern to match
            tenant_id: Tenant ID
            patient_ids: Optional list of patient IDs to search (None = all)
            limit: Maximum number of results
            
        Returns:
            List of matching patients with pattern details
        """
        logger.info(
            "Searching for temporal pattern",
            pattern_id=pattern.pattern_id,
            description=pattern.description,
        )
        
        matching_patients = []
        
        # Get patient IDs if not provided
        if not patient_ids:
            patient_ids = await self._get_all_patient_ids(tenant_id)
        
        # Check each patient's timeline
        for patient_id in patient_ids[:limit * 10]:  # Check more than limit for filtering
            timeline = await self._build_patient_timeline(patient_id, tenant_id)
            
            if not timeline:
                continue
            
            match_result = self._match_pattern_in_timeline(pattern, timeline)
            
            if match_result["matched"]:
                matching_patients.append({
                    "patient_id": patient_id,
                    "pattern_id": pattern.pattern_id,
                    "match_details": match_result,
                    "timeline_summary": timeline.to_dict(),
                })
                
                if len(matching_patients) >= limit:
                    break
        
        logger.info(
            "Pattern matching complete",
            pattern_id=pattern.pattern_id,
            matches_found=len(matching_patients),
        )
        
        return matching_patients
    
    def _match_pattern_in_timeline(
        self,
        pattern: TemporalPattern,
        timeline: VectorizedTimeline,
    ) -> Dict[str, Any]:
        """
        Match a pattern against a patient timeline.
        
        Returns:
            Dict with "matched": bool and match details
        """
        # Step 1: Find trigger events (e.g., SGLT2 start)
        trigger_events = [
            e for e in timeline.events
            if e.event_type == pattern.trigger_event_type
            and self._matches_filter(e, pattern.trigger_event_filter)
        ]
        
        if not trigger_events:
            return {"matched": False, "reason": "No trigger events found"}
        
        # Step 2: For each trigger event, find target events in time window
        for trigger_event in trigger_events:
            if trigger_event.time_offset_months is None:
                continue
            
            # Calculate time window
            window_start_months = trigger_event.time_offset_months
            window_end_months = trigger_event.time_offset_months + pattern.time_window_months
            
            # Find target events in window
            target_events = [
                e for e in timeline.events
                if e.event_type == pattern.target_event_type
                and e.time_offset_months is not None
                and window_start_months <= e.time_offset_months <= window_end_months
                and self._matches_filter(e, pattern.target_event_filter)
            ]
            
            if len(target_events) < 2:
                continue  # Need at least 2 events to detect change
            
            # Step 3: Check pattern condition
            if self._check_pattern_condition(pattern, trigger_event, target_events):
                return {
                    "matched": True,
                    "trigger_event": {
                        "id": trigger_event.id,
                        "date": trigger_event.event_date.isoformat(),
                        "time_offset_months": trigger_event.time_offset_months,
                    },
                    "target_events": [
                        {
                            "id": e.id,
                            "date": e.event_date.isoformat(),
                            "time_offset_months": e.time_offset_months,
                            "value": e.data.get("value"),
                        }
                        for e in target_events
                    ],
                    "pattern_details": {
                        "condition": pattern.condition,
                        "threshold": pattern.threshold,
                        "time_window_months": pattern.time_window_months,
                    },
                }
        
        return {"matched": False, "reason": "Pattern condition not met"}
    
    def _check_pattern_condition(
        self,
        pattern: TemporalPattern,
        trigger_event: TimelineEvent,
        target_events: List[TimelineEvent],
    ) -> bool:
        """
        Check if target events meet the pattern condition.
        
        Examples:
        - "drop_percentage > 0.2": 20% drop
        - "value_change < -20": Absolute decrease of 20
        - "increase_percentage > 0.1": 10% increase
        """
        if len(target_events) < 2:
            return False
        
        # Sort by time
        target_events.sort(key=lambda x: x.time_offset_months or 0)
        
        # Get baseline (first event) and comparison (last event)
        baseline_event = target_events[0]
        comparison_event = target_events[-1]
        
        baseline_value = self._extract_numeric_value(baseline_event)
        comparison_value = self._extract_numeric_value(comparison_event)
        
        if baseline_value is None or comparison_value is None:
            return False
        
        # Calculate change
        absolute_change = comparison_value - baseline_value
        percentage_change = absolute_change / baseline_value if baseline_value != 0 else 0
        
        # Check condition
        if pattern.condition == "drop_percentage":
            return percentage_change <= -pattern.threshold
        elif pattern.condition == "increase_percentage":
            return percentage_change >= pattern.threshold
        elif pattern.condition == "value_change":
            if pattern.direction == "decrease":
                return absolute_change <= pattern.threshold
            elif pattern.direction == "increase":
                return absolute_change >= pattern.threshold
            else:
                return abs(absolute_change) >= abs(pattern.threshold)
        elif pattern.condition == "absolute_value":
            if pattern.direction == "decrease":
                return comparison_value <= pattern.threshold
            elif pattern.direction == "increase":
                return comparison_value >= pattern.threshold
        
        return False
    
    def _extract_numeric_value(self, event: TimelineEvent) -> Optional[float]:
        """Extract numeric value from event data."""
        value = event.data.get("value")
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None
    
    def _matches_filter(self, event: TimelineEvent, filter_dict: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria."""
        if not filter_dict:
            return True
        
        for key, expected_value in filter_dict.items():
            event_value = event.data.get(key)
            
            # Handle code matching (case-insensitive)
            if key == "code" and event_value:
                if isinstance(expected_value, str):
                    return expected_value.lower() in str(event_value).lower()
            
            # Exact match
            if event_value != expected_value:
                return False
        
        return True
    
    async def _build_patient_timeline(
        self,
        patient_id: str,
        tenant_id: str,
    ) -> Optional[VectorizedTimeline]:
        """Build vectorized timeline for a patient."""
        from aegis.digital_twin.timeline import TimelineBuilder
        
        # Fetch patient events from database
        events = await self._fetch_patient_events(patient_id, tenant_id)
        
        if not events:
            return None
        
        # Build timeline
        timeline = await TimelineBuilder.build_timeline(
            patient_id=patient_id,
            events=events,
        )
        
        return timeline
    
    async def _fetch_patient_events(
        self,
        patient_id: str,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch patient events from database."""
        events = []
        
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    # Fetch conditions
                    conditions = await conn.fetch("""
                        SELECT 'condition' as type, created_at as date, 
                               jsonb_build_object('code', condition_code, 'description', description) as data
                        FROM conditions
                        WHERE patient_id = $1 AND tenant_id = $2
                        ORDER BY created_at
                    """, patient_id, tenant_id)
                    
                    # Fetch medications
                    medications = await conn.fetch("""
                        SELECT 'medication' as type, start_date as date,
                               jsonb_build_object('code', medication_code, 'name', medication_name) as data
                        FROM medications
                        WHERE patient_id = $1 AND tenant_id = $2
                        ORDER BY start_date
                    """, patient_id, tenant_id)
                    
                    # Fetch lab results
                    labs = await conn.fetch("""
                        SELECT 'lab' as type, result_date as date,
                               jsonb_build_object('code', lab_code, 'value', value, 'unit', unit) as data
                        FROM lab_results
                        WHERE patient_id = $1 AND tenant_id = $2
                        ORDER BY result_date
                    """, patient_id, tenant_id)
                    
                    # Combine all events
                    for row in conditions + medications + labs:
                        events.append({
                            "type": row["type"],
                            "date": row["date"],
                            "data": row["data"],
                        })
            except Exception as e:
                logger.error("Failed to fetch patient events", error=str(e), patient_id=patient_id)
        
        return events
    
    async def _get_all_patient_ids(self, tenant_id: str) -> List[str]:
        """Get all patient IDs for a tenant."""
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT id FROM patients WHERE tenant_id = $1 LIMIT 10000
                    """, tenant_id)
                    return [row["id"] for row in rows]
            except Exception as e:
                logger.error("Failed to fetch patient IDs", error=str(e))
        
        return []


# Predefined common patterns
COMMON_PATTERNS = {
    "egfr_drop_after_sglt2": TemporalPattern(
        pattern_id="egfr_drop_after_sglt2",
        description="eGFR drop > 20% within 3 months after SGLT2 inhibitor start",
        trigger_event_type="medication",
        trigger_event_filter={"code": "SGLT2"},
        target_event_type="lab",
        target_event_filter={"code": "eGFR"},
        time_window_months=3.0,
        condition="drop_percentage",
        threshold=0.2,
        direction="decrease",
    ),
    "potassium_spike_after_ace": TemporalPattern(
        pattern_id="potassium_spike_after_ace",
        description="Potassium > 6.0 within 1 month after ACE inhibitor start",
        trigger_event_type="medication",
        trigger_event_filter={"code": "ACE"},
        target_event_type="lab",
        target_event_filter={"code": "potassium"},
        time_window_months=1.0,
        condition="absolute_value",
        threshold=6.0,
        direction="increase",
    ),
    "hba1c_improvement": TemporalPattern(
        pattern_id="hba1c_improvement",
        description="HbA1c improvement > 1% within 6 months",
        trigger_event_type="medication",
        trigger_event_filter={"code": "diabetes_med"},
        target_event_type="lab",
        target_event_filter={"code": "HbA1c"},
        time_window_months=6.0,
        condition="increase_percentage",
        threshold=0.01,  # 1% improvement (decrease in HbA1c)
        direction="decrease",  # Lower HbA1c is better
    ),
}


async def query_temporal_pattern(
    pattern_name: str,
    tenant_id: str,
    patient_ids: Optional[List[str]] = None,
    limit: int = 100,
    db_pool=None,
    graph_client=None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to query a predefined temporal pattern.
    
    Args:
        pattern_name: Name of pattern (e.g., "egfr_drop_after_sglt2")
        tenant_id: Tenant ID
        patient_ids: Optional patient IDs to search
        limit: Maximum results
        db_pool: Database pool
        graph_client: Graph client
        
    Returns:
        List of matching patients
    """
    pattern = COMMON_PATTERNS.get(pattern_name)
    if not pattern:
        raise ValueError(f"Unknown pattern: {pattern_name}. Available: {list(COMMON_PATTERNS.keys())}")
    
    matcher = TemporalPatternMatcher(db_pool=db_pool, graph_client=graph_client)
    return await matcher.find_patients_matching_pattern(
        pattern=pattern,
        tenant_id=tenant_id,
        patient_ids=patient_ids,
        limit=limit,
    )
