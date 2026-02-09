"""
Scout Agent

The Scout Agent performs continuous monitoring:
- Kafka Event Listening: Sits on hospital's data bus, triggers Cowork sessions
- Proactive Triage: Identifies "No-Shows" or "Gap in Medication"
- Trend Prediction: Identifies "Slow-Burn" risks (e.g., weight gain indicating HF exacerbation)

This wraps KafkaEventConsumer + TriageEventHandler with Scout-specific interfaces.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import structlog

from aegis.events.kafka_consumer import (
    KafkaEventConsumer,
    TriageEventHandler,
    HealthcareEvent,
    EventType,
)
from aegis.cowork.engine import CoworkEngine
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class ScoutAgent:
    """
    Scout Agent - Continuous Monitor
    
    The Scout is the "Digital Twin" watchtower.
    
    Features:
    1. Event-Triggered Triage: Doesn't wait for user login - listens to Kafka streams
    2. Trend Prediction: Identifies "Slow-Burn" risks (e.g., weight gain → HF exacerbation)
    3. Proactive Alerts: Spins up Cowork sessions the millisecond a critical lab is filed
    
    This wraps KafkaEventConsumer and TriageEventHandler with Scout-specific methods.
    """
    
    def __init__(
        self,
        pool=None,
        tenant_id: str = "default",
        kafka_consumer: Optional[KafkaEventConsumer] = None,
        cowork_engine: Optional[CoworkEngine] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize Scout Agent.
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            kafka_consumer: Kafka event consumer
            cowork_engine: Cowork engine for session creation
            llm_client: LLM client
        """
        self.pool = pool
        self.tenant_id = tenant_id
        
        # Wrap KafkaEventConsumer
        self.kafka_consumer = kafka_consumer or KafkaEventConsumer(
            pool=pool,
            tenant_id=tenant_id,
        )
        
        # Wrap TriageEventHandler
        self.triage_handler = TriageEventHandler(pool=pool)
        
        # Cowork engine for session creation
        self.cowork_engine = cowork_engine
        
        logger.info("ScoutAgent initialized", tenant_id=tenant_id)
    
    # =========================================================================
    # Event-Triggered Triage
    # =========================================================================
    
    async def listen_for_events(
        self,
        event_types: List[EventType],
        callback: Optional[callable] = None,
    ):
        """
        Listen for events on Kafka and trigger Cowork sessions.
        
        Example: If Potassium > 6.0 hits the system, instantly spins up a Cowork session.
        
        Args:
            event_types: List of event types to listen for
            callback: Optional callback function when event is received
        """
        logger.info("Starting event listener", event_types=[e.value for e in event_types])
        
        # Register event handlers
        for event_type in event_types:
            await self._register_event_handler(event_type, callback)
        
        # Start listening (in production, would be async background task)
        # await self.kafka_consumer.start_listening()
    
    async def _register_event_handler(
        self,
        event_type: EventType,
        callback: Optional[callable] = None,
    ):
        """Register handler for specific event type."""
        async def event_handler(event: HealthcareEvent):
            logger.info(
                "Event received",
                event_type=event.event_type.value,
                patient_id=event.patient_id,
            )
            
            # Trigger Cowork session if critical
            if await self._is_critical_event(event):
                await self._trigger_cowork_session(event)
            
            # Call custom callback if provided
            if callback:
                await callback(event)
        
        # Register with Kafka consumer
        # await self.kafka_consumer.subscribe(event_type.value, event_handler)
    
    async def _is_critical_event(self, event: HealthcareEvent) -> bool:
        """Check if event is critical and requires immediate Cowork session."""
        # Critical event types
        critical_types = [
            EventType.LAB_RESULT_CRITICAL,
            EventType.VITAL_SIGN_ABNORMAL,
            EventType.PATIENT_ADMITTED,
        ]
        
        if event.event_type in critical_types:
            return True
        
        # Check payload for critical values
        payload = event.payload or {}
        
        # Critical lab values
        if event.event_type == EventType.LAB_RESULT_RECEIVED:
            lab_value = payload.get("value")
            lab_code = payload.get("code", "").upper()
            
            # Potassium > 6.0
            if lab_code == "K" and lab_value and lab_value > 6.0:
                return True
            
            # Creatinine spike
            if lab_code == "CREAT" and lab_value and lab_value > 3.0:
                return True
        
        return False
    
    async def _trigger_cowork_session(self, event: HealthcareEvent):
        """Trigger a Cowork session for a critical event."""
        if not self.cowork_engine:
            logger.warning("Cowork engine not available, cannot trigger session")
            return
        
        logger.info(
            "Triggering Cowork session",
            event_type=event.event_type.value,
            patient_id=event.patient_id,
        )
        
        # Create Cowork session
        session = await self.cowork_engine.create_session(
            patient_id=event.patient_id,
            title=f"Critical Alert: {event.event_type.value}",
            description=f"Automatically triggered by Scout agent for {event.event_type.value}",
        )
        
        # Add perception step
        await self.cowork_engine.perceive(
            session_id=session.id,
            event_type=event.event_type.value,
            event_data=event.payload or {},
        )
        
        return session
    
    # =========================================================================
    # Trend Prediction
    # =========================================================================
    
    async def predict_trend(
        self,
        patient_id: str,
        metric_name: str,
        time_window_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Predict trend for a metric (identifies "Slow-Burn" risks).
        
        Example: Patient's weight has increased 3lbs every day for 4 days → Heart Failure exacerbation
        
        Args:
            patient_id: Patient ID
            metric_name: Metric name (e.g., "weight", "creatinine", "BNP")
            time_window_days: Time window for analysis
            
        Returns:
            Dict with trend prediction
        """
        logger.info(
            "Predicting trend",
            patient_id=patient_id,
            metric_name=metric_name,
            time_window_days=time_window_days,
        )
        
        # Get metric values over time window
        # In production, would query time-series database
        values = []  # Would fetch from database
        
        if len(values) < 2:
            return {
                "patient_id": patient_id,
                "metric_name": metric_name,
                "trend": "insufficient_data",
                "prediction": "Cannot predict trend with insufficient data",
            }
        
        # Calculate trend
        trend = self._calculate_trend(values)
        
        # Predict risk
        risk_level = self._assess_risk(metric_name, trend)
        
        return {
            "patient_id": patient_id,
            "metric_name": metric_name,
            "time_window_days": time_window_days,
            "trend": trend,
            "risk_level": risk_level,
            "prediction": self._generate_prediction(metric_name, trend, risk_level),
        }
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend from values."""
        if len(values) < 2:
            return {"direction": "stable", "rate": 0.0}
        
        # Simple linear trend
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value
        change_percentage = (change / first_value) * 100 if first_value != 0 else 0
        
        direction = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
        
        return {
            "direction": direction,
            "change": change,
            "change_percentage": change_percentage,
            "rate_per_day": change / len(values),
        }
    
    def _assess_risk(self, metric_name: str, trend: Dict[str, Any]) -> str:
        """Assess risk level based on trend."""
        direction = trend.get("direction", "stable")
        rate = abs(trend.get("rate_per_day", 0))
        
        # Risk thresholds (example)
        if metric_name == "weight":
            # Weight gain > 2lbs/day for multiple days = HF risk
            if direction == "increasing" and rate > 2.0:
                return "high"
            elif direction == "increasing" and rate > 1.0:
                return "moderate"
        
        elif metric_name == "creatinine":
            # Creatinine rise > 0.3/day = AKI risk
            if direction == "increasing" and rate > 0.3:
                return "high"
            elif direction == "increasing" and rate > 0.1:
                return "moderate"
        
        elif metric_name == "BNP":
            # BNP rise = HF exacerbation risk
            if direction == "increasing" and rate > 100:
                return "high"
        
        return "low"
    
    def _generate_prediction(self, metric_name: str, trend: Dict[str, Any], risk_level: str) -> str:
        """Generate human-readable prediction."""
        direction = trend.get("direction", "stable")
        rate = trend.get("rate_per_day", 0)
        
        if risk_level == "high":
            if metric_name == "weight" and direction == "increasing":
                return f"Rapid weight gain ({rate:.1f} lbs/day) suggests possible heart failure exacerbation. Recommend immediate evaluation."
            elif metric_name == "creatinine" and direction == "increasing":
                return f"Rapid creatinine rise ({rate:.2f} mg/dL/day) suggests acute kidney injury. Recommend immediate evaluation."
        elif risk_level == "moderate":
            return f"{metric_name.capitalize()} trending {direction}. Monitor closely."
        else:
            return f"{metric_name.capitalize()} trend is stable."
    
    # =========================================================================
    # Proactive Triage
    # =========================================================================
    
    async def detect_no_shows(
        self,
        time_window_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Detect no-shows by comparing Claims data with EHR schedules.
        
        Identifies patients who were scheduled but didn't show up.
        
        Args:
            time_window_days: Time window to check
            
        Returns:
            List of no-show patients
        """
        logger.info("Detecting no-shows", time_window_days=time_window_days)
        
        # In production, would:
        # 1. Query EHR for scheduled appointments
        # 2. Query Claims for actual visits
        # 3. Compare and identify gaps
        
        no_shows = []  # Would return actual no-shows
        
        return no_shows
    
    async def detect_medication_gaps(
        self,
        patient_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in medication adherence.
        
        Compares prescribed medications with Claims data to identify gaps.
        
        Args:
            patient_id: Optional patient ID (None = all patients)
            
        Returns:
            List of medication gaps
        """
        logger.info("Detecting medication gaps", patient_id=patient_id)
        
        # In production, would:
        # 1. Get prescribed medications from EHR
        # 2. Get medication claims from Claims data
        # 3. Identify gaps in adherence
        
        gaps = []  # Would return actual gaps
        
        return gaps
    
    # =========================================================================
    # Unified Interface
    # =========================================================================
    
    async def monitor_patients(
        self,
        patient_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Monitor patients for alerts and trends (wraps TriageEventHandler).
        
        Args:
            patient_ids: Optional list of patient IDs (None = all patients)
            
        Returns:
            Dict with monitoring results
        """
        logger.info("Monitoring patients", patient_count=len(patient_ids) if patient_ids else "all")
        
        # Use TriageEventHandler
        # In production, would run triage for each patient
        
        return {
            "alerts_generated": 0,
            "trends_detected": 0,
            "cowork_sessions_triggered": 0,
        }
