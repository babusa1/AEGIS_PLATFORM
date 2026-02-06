"""
Recursive Summarization

Pre-digest patient charts into hierarchical summaries:
- Daily summaries → Weekly summaries → Monthly summaries → Yearly summaries

This reduces token usage and improves retrieval for long patient histories.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SummaryLevel:
    """Summary level configuration."""
    name: str
    time_window_days: int
    max_tokens: int
    include_details: bool


class RecursiveSummarizer:
    """
    Recursive summarization for patient charts.
    
    Creates hierarchical summaries:
    - Level 1: Daily summaries (raw events → daily)
    - Level 2: Weekly summaries (daily → weekly)
    - Level 3: Monthly summaries (weekly → monthly)
    - Level 4: Yearly summaries (monthly → yearly)
    """
    
    # Summary levels
    LEVELS = [
        SummaryLevel("daily", 1, 500, True),
        SummaryLevel("weekly", 7, 1000, True),
        SummaryLevel("monthly", 30, 2000, False),
        SummaryLevel("yearly", 365, 3000, False),
    ]
    
    def __init__(self, llm_client=None):
        """
        Initialize recursive summarizer.
        
        Args:
            llm_client: LLM client for generating summaries
        """
        self.llm_client = llm_client
    
    async def summarize_patient_chart(
        self,
        patient_id: str,
        events: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        level: str = "monthly",
    ) -> Dict[str, Any]:
        """
        Summarize a patient chart recursively.
        
        Args:
            patient_id: Patient ID
            events: List of events/encounters/labs/etc. with timestamps
            start_date: Start of time period
            end_date: End of time period
            level: Summary level (daily, weekly, monthly, yearly)
            
        Returns:
            Summary dict with:
            - summary_text: Generated summary
            - level: Summary level
            - time_period: Start/end dates
            - key_events: Important events extracted
            - statistics: Counts, trends, etc.
        """
        if not events:
            return {
                "patient_id": patient_id,
                "summary_text": "No events in this period.",
                "level": level,
                "time_period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "key_events": [],
                "statistics": {},
            }
        
        # Group events by time window based on level
        level_config = next((l for l in self.LEVELS if l.name == level), self.LEVELS[2])  # Default: monthly
        grouped_events = self._group_events_by_window(events, start_date, end_date, level_config.time_window_days)
        
        # Generate summaries for each window
        window_summaries = []
        for window_start, window_events in grouped_events.items():
            window_summary = await self._summarize_window(
                window_events,
                window_start,
                level_config,
            )
            window_summaries.append(window_summary)
        
        # Combine window summaries into final summary
        combined_summary = await self._combine_summaries(
            window_summaries,
            patient_id,
            start_date,
            end_date,
            level_config,
        )
        
        # Extract key events and statistics
        key_events = self._extract_key_events(events)
        statistics = self._calculate_statistics(events)
        
        return {
            "patient_id": patient_id,
            "summary_text": combined_summary,
            "level": level,
            "time_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "key_events": key_events,
            "statistics": statistics,
            "window_count": len(grouped_events),
        }
    
    def _group_events_by_window(
        self,
        events: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        window_days: int,
    ) -> Dict[datetime, List[Dict[str, Any]]]:
        """Group events into time windows."""
        grouped = {}
        current = start_date
        
        while current < end_date:
            window_end = current + timedelta(days=window_days)
            window_events = [
                e for e in events
                if self._get_event_date(e) >= current and self._get_event_date(e) < window_end
            ]
            if window_events:
                grouped[current] = window_events
            current = window_end
        
        return grouped
    
    def _get_event_date(self, event: Dict[str, Any]) -> datetime:
        """Extract date from event."""
        date_str = event.get("date") or event.get("timestamp") or event.get("effective_date")
        if isinstance(date_str, str):
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                pass
        elif isinstance(date_str, datetime):
            return date_str
        return datetime.utcnow()
    
    async def _summarize_window(
        self,
        events: List[Dict[str, Any]],
        window_start: datetime,
        level_config: SummaryLevel,
    ) -> str:
        """
        Summarize events in a single time window.
        
        Uses LLM if available, otherwise creates structured summary.
        """
        if not self.llm_client:
            # Fallback: structured summary
            return self._create_structured_summary(events, window_start, level_config)
        
        try:
            # Build prompt for LLM summarization
            events_text = self._format_events_for_summary(events)
            
            prompt = f"""Summarize these healthcare events for a patient in a concise, clinical format.

Time Period: {window_start.strftime('%Y-%m-%d')} to {(window_start + timedelta(days=level_config.time_window_days)).strftime('%Y-%m-%d')}

Events:
{events_text}

Provide a summary that includes:
1. Key diagnoses or conditions
2. Important procedures or treatments
3. Significant lab results or vital signs
4. Medication changes
5. Care team interactions

Keep it under {level_config.max_tokens} tokens and focus on clinically relevant information.
"""
            
            response = await self.llm_client.generate(prompt, max_tokens=level_config.max_tokens)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error("LLM summarization failed, using fallback", error=str(e))
            return self._create_structured_summary(events, window_start, level_config)
    
    def _format_events_for_summary(self, events: List[Dict[str, Any]]) -> str:
        """Format events as text for LLM."""
        lines = []
        for i, event in enumerate(events[:50], 1):  # Limit to 50 events
            event_type = event.get("type") or event.get("resource_type", "event")
            date = self._get_event_date(event).strftime("%Y-%m-%d")
            description = event.get("description") or event.get("text") or event.get("code", {}).get("text", "")
            
            lines.append(f"{i}. [{date}] {event_type}: {description}")
        
        if len(events) > 50:
            lines.append(f"\n... and {len(events) - 50} more events")
        
        return "\n".join(lines)
    
    def _create_structured_summary(
        self,
        events: List[Dict[str, Any]],
        window_start: datetime,
        level_config: SummaryLevel,
    ) -> str:
        """Create structured summary without LLM."""
        summary_parts = []
        summary_parts.append(f"Period: {window_start.strftime('%Y-%m-%d')}")
        summary_parts.append(f"Total Events: {len(events)}")
        
        # Group by event type
        by_type = {}
        for event in events:
            event_type = event.get("type") or event.get("resource_type", "unknown")
            by_type[event_type] = by_type.get(event_type, 0) + 1
        
        summary_parts.append("\nEvent Types:")
        for event_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            summary_parts.append(f"  - {event_type}: {count}")
        
        # Key events (diagnoses, procedures, medications)
        key_types = ["condition", "procedure", "medication", "observation", "encounter"]
        key_events = [e for e in events if (e.get("type") or "").lower() in key_types]
        
        if key_events:
            summary_parts.append(f"\nKey Events ({len(key_events)}):")
            for event in key_events[:10]:  # Top 10
                date = self._get_event_date(event).strftime("%Y-%m-%d")
                event_type = event.get("type") or "event"
                description = event.get("description") or event.get("code", {}).get("text", "")
                summary_parts.append(f"  - [{date}] {event_type}: {description[:100]}")
        
        return "\n".join(summary_parts)
    
    async def _combine_summaries(
        self,
        window_summaries: List[str],
        patient_id: str,
        start_date: datetime,
        end_date: datetime,
        level_config: SummaryLevel,
    ) -> str:
        """Combine multiple window summaries into one."""
        if len(window_summaries) == 1:
            return window_summaries[0]
        
        if self.llm_client:
            try:
                combined_text = "\n\n---\n\n".join(window_summaries)
                prompt = f"""Combine these {len(window_summaries)} summaries into a single cohesive summary for patient {patient_id}.

Time Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}

Summaries:
{combined_text}

Create a unified summary that highlights:
- Overall health trends
- Major changes or events
- Ongoing conditions or treatments
- Key care milestones

Keep it concise and clinically relevant.
"""
                response = await self.llm_client.generate(prompt, max_tokens=level_config.max_tokens)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error("LLM combination failed", error=str(e))
        
        # Fallback: simple concatenation
        return "\n\n---\n\n".join(window_summaries)
    
    def _extract_key_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key events (diagnoses, procedures, hospitalizations)."""
        key_types = ["condition", "procedure", "encounter", "medication", "observation"]
        key_events = []
        
        for event in events:
            event_type = (event.get("type") or event.get("resource_type", "")).lower()
            if event_type in key_types:
                key_events.append({
                    "type": event_type,
                    "date": self._get_event_date(event).isoformat(),
                    "description": event.get("description") or event.get("code", {}).get("text", ""),
                    "id": event.get("id"),
                })
        
        # Sort by date, most recent first
        key_events.sort(key=lambda x: x["date"], reverse=True)
        
        return key_events[:20]  # Top 20
    
    def _calculate_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from events."""
        stats = {
            "total_events": len(events),
            "by_type": {},
            "date_range": {},
        }
        
        if events:
            dates = [self._get_event_date(e) for e in events]
            stats["date_range"] = {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat(),
            }
        
        for event in events:
            event_type = event.get("type") or event.get("resource_type", "unknown")
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1
        
        return stats


async def pre_digest_patient_chart(
    patient_id: str,
    events: List[Dict[str, Any]],
    llm_client=None,
) -> Dict[str, Any]:
    """
    Convenience function to pre-digest a patient chart.
    
    Creates monthly summaries for the past year.
    """
    summarizer = RecursiveSummarizer(llm_client=llm_client)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    
    return await summarizer.summarize_patient_chart(
        patient_id=patient_id,
        events=events,
        start_date=start_date,
        end_date=end_date,
        level="monthly",
    )
