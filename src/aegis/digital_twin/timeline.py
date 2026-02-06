"""
Digital Twin Timeline with Vectorized Events

Builds a Live Digital Twin with vectorized timelines where every patient event
includes a Time_Offset from the initial diagnosis, enabling temporal pattern matching.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TimelineEvent:
    """A patient event with temporal context."""
    id: str
    event_type: str  # condition, medication, lab, procedure, etc.
    event_date: datetime
    data: Dict[str, Any]
    
    # Temporal context
    time_offset_days: Optional[int] = None  # Days from initial diagnosis
    time_offset_months: Optional[float] = None  # Months from initial diagnosis
    initial_diagnosis_date: Optional[datetime] = None
    
    # Vector representation (for pattern matching)
    vector: Optional[List[float]] = None
    
    # Metadata
    source_system: Optional[str] = None
    tenant_id: Optional[str] = None


class VectorizedTimeline:
    """
    Vectorized timeline for a patient.
    
    Every event is converted into a vector that includes Time_Offset from
    the initial diagnosis, enabling pattern matching queries like:
    "Patients who showed a 20% drop in eGFR within 3 months of starting SGLT2"
    """
    
    def __init__(self, patient_id: str, initial_diagnosis_date: Optional[datetime] = None):
        """
        Initialize vectorized timeline.
        
        Args:
            patient_id: Patient ID
            initial_diagnosis_date: Date of initial diagnosis (for Time_Offset calculation)
        """
        self.patient_id = patient_id
        self.initial_diagnosis_date = initial_diagnosis_date
        self.events: List[TimelineEvent] = []
    
    def add_event(
        self,
        event_type: str,
        event_date: datetime,
        data: Dict[str, Any],
        source_system: Optional[str] = None,
    ) -> TimelineEvent:
        """
        Add an event to the timeline with Time_Offset calculation.
        
        Args:
            event_type: Type of event
            event_date: When the event occurred
            data: Event data
            source_system: Source system name
            
        Returns:
            TimelineEvent with Time_Offset calculated
        """
        # Calculate Time_Offset from initial diagnosis
        time_offset_days = None
        time_offset_months = None
        
        if self.initial_diagnosis_date:
            delta = event_date - self.initial_diagnosis_date
            time_offset_days = delta.days
            time_offset_months = delta.days / 30.44  # Average days per month
        
        event = TimelineEvent(
            id=f"{self.patient_id}:{event_type}:{event_date.isoformat()}",
            event_type=event_type,
            event_date=event_date,
            data=data,
            time_offset_days=time_offset_days,
            time_offset_months=time_offset_months,
            initial_diagnosis_date=self.initial_diagnosis_date,
            source_system=source_system,
        )
        
        # Vectorize event (simplified - in production would use embeddings)
        event.vector = self._vectorize_event(event)
        
        self.events.append(event)
        return event
    
    def _vectorize_event(self, event: TimelineEvent) -> List[float]:
        """
        Convert event to vector representation.
        
        Vector includes:
        - Time_Offset (normalized)
        - Event type encoding
        - Key data values (normalized)
        """
        vector = []
        
        # Time_Offset component (normalized to 0-1)
        if event.time_offset_months is not None:
            # Normalize: assume max 10 years = 120 months
            normalized_time = min(1.0, abs(event.time_offset_months) / 120.0)
            vector.append(normalized_time)
        else:
            vector.append(0.0)
        
        # Event type encoding (one-hot style)
        event_types = ["condition", "medication", "lab", "procedure", "encounter", "vital"]
        for et in event_types:
            vector.append(1.0 if event.event_type == et else 0.0)
        
        # Key data values (extract numeric values if present)
        # For labs: value, for medications: dose, etc.
        if "value" in event.data:
            try:
                value = float(event.data["value"])
                # Normalize (assume max 1000)
                vector.append(min(1.0, value / 1000.0))
            except (ValueError, TypeError):
                vector.append(0.0)
        else:
            vector.append(0.0)
        
        return vector
    
    def find_pattern(
        self,
        pattern_type: str,
        time_window_months: float,
        threshold: float = 0.2,
    ) -> List[TimelineEvent]:
        """
        Find temporal patterns in the timeline.
        
        Example patterns:
        - "egfr_drop": Find eGFR drops within time window
        - "medication_start": Find medication starts
        - "condition_change": Find condition changes
        
        Args:
            pattern_type: Type of pattern to find
            time_window_months: Time window in months
            threshold: Threshold for pattern detection (e.g., 0.2 = 20% drop)
            
        Returns:
            List of events matching the pattern
        """
        matching_events = []
        
        if pattern_type == "egfr_drop":
            # Find eGFR drops within time window
            egfr_events = [e for e in self.events if e.event_type == "lab" and "egfr" in str(e.data.get("code", "")).lower()]
            egfr_events.sort(key=lambda x: x.event_date)
            
            for i in range(1, len(egfr_events)):
                prev_event = egfr_events[i-1]
                curr_event = egfr_events[i]
                
                # Check if within time window
                if curr_event.time_offset_months and prev_event.time_offset_months:
                    time_diff = abs(curr_event.time_offset_months - prev_event.time_offset_months)
                    if time_diff <= time_window_months:
                        # Check for drop
                        prev_value = float(prev_event.data.get("value", 0))
                        curr_value = float(curr_event.data.get("value", 0))
                        
                        if prev_value > 0:
                            drop_pct = (prev_value - curr_value) / prev_value
                            if drop_pct >= threshold:
                                matching_events.append(curr_event)
        
        return matching_events
    
    def get_events_in_window(
        self,
        start_offset_months: float,
        end_offset_months: float,
    ) -> List[TimelineEvent]:
        """Get events within a time offset window."""
        return [
            e for e in self.events
            if e.time_offset_months is not None
            and start_offset_months <= e.time_offset_months <= end_offset_months
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timeline to dictionary."""
        return {
            "patient_id": self.patient_id,
            "initial_diagnosis_date": self.initial_diagnosis_date.isoformat() if self.initial_diagnosis_date else None,
            "event_count": len(self.events),
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "event_date": e.event_date.isoformat(),
                    "time_offset_days": e.time_offset_days,
                    "time_offset_months": e.time_offset_months,
                    "data": e.data,
                }
                for e in self.events
            ],
        }


class TimelineBuilder:
    """Builder for creating vectorized timelines from patient data."""
    
    @staticmethod
    async def build_timeline(
        patient_id: str,
        events: List[Dict[str, Any]],
        initial_diagnosis_date: Optional[datetime] = None,
    ) -> VectorizedTimeline:
        """
        Build a vectorized timeline from patient events.
        
        Args:
            patient_id: Patient ID
            events: List of event dictionaries with 'type', 'date', 'data'
            initial_diagnosis_date: Initial diagnosis date (if not provided, uses first condition)
            
        Returns:
            VectorizedTimeline
        """
        timeline = VectorizedTimeline(patient_id, initial_diagnosis_date)
        
        # Find initial diagnosis if not provided
        if not initial_diagnosis_date:
            condition_events = [e for e in events if e.get("type") == "condition"]
            if condition_events:
                first_condition = min(condition_events, key=lambda x: x.get("date", datetime.max))
                initial_diagnosis_date = first_condition.get("date")
                timeline.initial_diagnosis_date = initial_diagnosis_date
        
        # Add all events
        for event in events:
            event_date = event.get("date")
            if isinstance(event_date, str):
                event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            
            timeline.add_event(
                event_type=event.get("type", "unknown"),
                event_date=event_date or datetime.utcnow(),
                data=event.get("data", {}),
                source_system=event.get("source_system"),
            )
        
        return timeline
