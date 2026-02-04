"""
Kafka Event-Driven Agent System

Real-time event processing that triggers agents automatically:
- Patient admission events → Triage Agent
- Lab result events → Alert generation
- Claim submission → Denial prediction
- Discharge events → Readmission risk assessment
"""

from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import json

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Event Types
# =============================================================================

class EventType(str, Enum):
    """Healthcare event types."""
    # Patient events
    PATIENT_ADMITTED = "patient.admitted"
    PATIENT_DISCHARGED = "patient.discharged"
    PATIENT_TRANSFERRED = "patient.transferred"
    PATIENT_UPDATED = "patient.updated"
    
    # Clinical events
    LAB_RESULT_RECEIVED = "lab.result.received"
    LAB_RESULT_CRITICAL = "lab.result.critical"
    VITAL_SIGN_ABNORMAL = "vital.abnormal"
    CONDITION_DIAGNOSED = "condition.diagnosed"
    MEDICATION_PRESCRIBED = "medication.prescribed"
    
    # Revenue cycle events
    CLAIM_SUBMITTED = "claim.submitted"
    CLAIM_ADJUDICATED = "claim.adjudicated"
    CLAIM_DENIED = "claim.denied"
    DENIAL_APPEALED = "denial.appealed"
    
    # Care events
    ENCOUNTER_STARTED = "encounter.started"
    ENCOUNTER_COMPLETED = "encounter.completed"
    ORDER_PLACED = "order.placed"
    
    # System events
    DATA_INGESTED = "data.ingested"
    ALERT_GENERATED = "alert.generated"


class EventPriority(str, Enum):
    """Event processing priority."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# =============================================================================
# Event Models
# =============================================================================

class HealthcareEvent(BaseModel):
    """Base healthcare event."""
    event_id: str
    event_type: EventType
    priority: EventPriority = EventPriority.NORMAL
    
    # Source
    tenant_id: str
    source_system: str = "unknown"
    
    # Payload
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventResult(BaseModel):
    """Result of event processing."""
    event_id: str
    handler: str
    status: str  # success, failure, skipped
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    processing_time_ms: int = 0
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Event Handlers
# =============================================================================

class EventHandler:
    """Base event handler."""
    
    def __init__(self, name: str, event_types: List[EventType]):
        self.name = name
        self.event_types = event_types
    
    async def handle(self, event: HealthcareEvent) -> EventResult:
        """Handle event. Override in subclasses."""
        raise NotImplementedError
    
    def can_handle(self, event: HealthcareEvent) -> bool:
        """Check if handler can process this event."""
        return event.event_type in self.event_types


class TriageEventHandler(EventHandler):
    """
    Handle clinical events with Triage Agent.
    
    Triggers on:
    - Lab results (especially critical)
    - Abnormal vitals
    - Patient admissions
    """
    
    def __init__(self, pool=None):
        super().__init__(
            name="triage_handler",
            event_types=[
                EventType.LAB_RESULT_RECEIVED,
                EventType.LAB_RESULT_CRITICAL,
                EventType.VITAL_SIGN_ABNORMAL,
                EventType.PATIENT_ADMITTED,
            ]
        )
        self.pool = pool
    
    async def handle(self, event: HealthcareEvent) -> EventResult:
        """Process clinical event through triage agent."""
        import time
        start = time.time()
        
        try:
            from aegis.agents.triage import TriageAgent
            
            agent = TriageAgent(self.pool, event.tenant_id)
            
            # Run triage for specific patient
            if event.patient_id:
                result = await agent.run(
                    f"Triage patient {event.patient_id} - {event.event_type.value}"
                )
            else:
                result = await agent.run()
            
            processing_time = int((time.time() - start) * 1000)
            
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="success",
                result={
                    "alerts_generated": len(result.get("alerts", [])),
                    "priority_counts": result.get("priority_counts", {}),
                    "report": result.get("report", "")[:500],
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Triage handler failed: {e}")
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="failure",
                error=str(e),
                processing_time_ms=int((time.time() - start) * 1000),
            )


class DenialPredictionHandler(EventHandler):
    """
    Handle claim events with Denial Prediction.
    
    Triggers on:
    - Claim submissions (pre-submission check)
    - Claim denials (for pattern analysis)
    """
    
    def __init__(self, pool=None):
        super().__init__(
            name="denial_prediction_handler",
            event_types=[
                EventType.CLAIM_SUBMITTED,
                EventType.CLAIM_DENIED,
            ]
        )
        self.pool = pool
    
    async def handle(self, event: HealthcareEvent) -> EventResult:
        """Process claim event through denial prediction."""
        import time
        start = time.time()
        
        try:
            from aegis.ml.denial_prediction import get_denial_predictor
            
            predictor = get_denial_predictor()
            
            # Get claim data from event payload
            claim = event.payload.get("claim", {})
            if not claim and event.resource_id:
                claim = {"id": event.resource_id}
            
            prediction = await predictor.predict(claim)
            
            processing_time = int((time.time() - start) * 1000)
            
            # Generate alert if high risk
            alert_generated = prediction.risk_level in ["high", "critical"]
            
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="success",
                result={
                    "claim_id": prediction.claim_id,
                    "denial_probability": prediction.denial_probability,
                    "risk_level": prediction.risk_level,
                    "primary_reason": prediction.primary_reason.value if prediction.primary_reason else None,
                    "alert_generated": alert_generated,
                    "recommendations": prediction.recommendations[:3],
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Denial prediction handler failed: {e}")
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="failure",
                error=str(e),
                processing_time_ms=int((time.time() - start) * 1000),
            )


class ReadmissionRiskHandler(EventHandler):
    """
    Handle discharge events with Readmission Prediction.
    
    Triggers on:
    - Patient discharges
    - Encounter completions
    """
    
    def __init__(self, pool=None):
        super().__init__(
            name="readmission_risk_handler",
            event_types=[
                EventType.PATIENT_DISCHARGED,
                EventType.ENCOUNTER_COMPLETED,
            ]
        )
        self.pool = pool
    
    async def handle(self, event: HealthcareEvent) -> EventResult:
        """Process discharge event through readmission prediction."""
        import time
        start = time.time()
        
        try:
            from aegis.ml.readmission_prediction import get_readmission_predictor
            
            predictor = get_readmission_predictor()
            
            if not event.patient_id:
                return EventResult(
                    event_id=event.event_id,
                    handler=self.name,
                    status="skipped",
                    result={"reason": "No patient_id in event"},
                )
            
            prediction = await predictor.predict(
                patient_id=event.patient_id,
                encounter_data=event.payload.get("encounter", {}),
            )
            
            processing_time = int((time.time() - start) * 1000)
            
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="success",
                result={
                    "patient_id": prediction.patient_id,
                    "risk_level": prediction.risk_level.value,
                    "probability_30day": prediction.readmission_probability_30day,
                    "lace_score": prediction.lace_score.total_score,
                    "interventions_count": len(prediction.recommended_interventions),
                    "urgent_interventions": [
                        i.intervention for i in prediction.recommended_interventions
                        if i.priority.value == "urgent"
                    ],
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Readmission risk handler failed: {e}")
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="failure",
                error=str(e),
                processing_time_ms=int((time.time() - start) * 1000),
            )


class AlertNotificationHandler(EventHandler):
    """
    Handle alert events by sending notifications.
    
    Triggers on:
    - Alert generated events
    - Critical lab results
    """
    
    def __init__(self, notification_service=None):
        super().__init__(
            name="alert_notification_handler",
            event_types=[
                EventType.ALERT_GENERATED,
                EventType.LAB_RESULT_CRITICAL,
            ]
        )
        self.notification_service = notification_service
    
    async def handle(self, event: HealthcareEvent) -> EventResult:
        """Process alert by sending notifications."""
        import time
        start = time.time()
        
        try:
            # In production, would send to notification service
            alert_data = event.payload
            
            # For now, log the alert
            logger.info(
                "Alert notification",
                event_type=event.event_type.value,
                patient_id=event.patient_id,
                alert=alert_data,
            )
            
            processing_time = int((time.time() - start) * 1000)
            
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="success",
                result={
                    "notification_sent": True,
                    "channels": ["log"],  # Would include slack, email, etc.
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            return EventResult(
                event_id=event.event_id,
                handler=self.name,
                status="failure",
                error=str(e),
            )


# =============================================================================
# Kafka Consumer
# =============================================================================

class KafkaEventConsumer:
    """
    Kafka consumer for healthcare events.
    
    Consumes events from Kafka topics and dispatches to handlers.
    """
    
    TOPIC_MAPPING = {
        "aegis.patients": [EventType.PATIENT_ADMITTED, EventType.PATIENT_DISCHARGED, EventType.PATIENT_UPDATED],
        "aegis.clinical": [EventType.LAB_RESULT_RECEIVED, EventType.LAB_RESULT_CRITICAL, EventType.VITAL_SIGN_ABNORMAL],
        "aegis.claims": [EventType.CLAIM_SUBMITTED, EventType.CLAIM_DENIED, EventType.CLAIM_ADJUDICATED],
        "aegis.encounters": [EventType.ENCOUNTER_STARTED, EventType.ENCOUNTER_COMPLETED],
        "aegis.alerts": [EventType.ALERT_GENERATED],
    }
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "aegis-event-processor",
        pool=None,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.pool = pool
        
        self._consumer = None
        self._running = False
        self._handlers: List[EventHandler] = []
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self._handlers = [
            TriageEventHandler(self.pool),
            DenialPredictionHandler(self.pool),
            ReadmissionRiskHandler(self.pool),
            AlertNotificationHandler(),
        ]
    
    def register_handler(self, handler: EventHandler):
        """Register a custom event handler."""
        self._handlers.append(handler)
    
    async def start(self):
        """Start consuming events."""
        try:
            from aiokafka import AIOKafkaConsumer
            
            self._consumer = AIOKafkaConsumer(
                *self.TOPIC_MAPPING.keys(),
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
            )
            
            await self._consumer.start()
            self._running = True
            
            logger.info(
                "Kafka consumer started",
                topics=list(self.TOPIC_MAPPING.keys()),
                group_id=self.group_id,
            )
            
            # Start consuming
            asyncio.create_task(self._consume_loop())
            
        except ImportError:
            logger.warning("aiokafka not installed - using mock consumer")
            self._running = True
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop consuming events."""
        self._running = False
        
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def _consume_loop(self):
        """Main consume loop."""
        while self._running:
            try:
                async for message in self._consumer:
                    if not self._running:
                        break
                    
                    await self._process_message(message)
                    
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _process_message(self, message):
        """Process a single Kafka message."""
        try:
            # Parse event
            event_data = message.value
            event = HealthcareEvent(**event_data)
            
            logger.info(
                "Processing event",
                event_id=event.event_id,
                event_type=event.event_type.value,
                patient_id=event.patient_id,
            )
            
            # Find and run handlers
            for handler in self._handlers:
                if handler.can_handle(event):
                    result = await handler.handle(event)
                    
                    logger.info(
                        "Handler completed",
                        handler=handler.name,
                        status=result.status,
                        processing_time_ms=result.processing_time_ms,
                    )
                    
                    # Store result (would go to database/metrics in production)
                    await self._store_result(result)
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
    
    async def _store_result(self, result: EventResult):
        """Store event processing result."""
        # In production, would store to database/metrics
        pass
    
    async def publish_event(self, event: HealthcareEvent, topic: str = None):
        """
        Publish an event (for testing/internal use).
        
        In production, would use a proper producer.
        """
        if not topic:
            # Determine topic from event type
            for t, types in self.TOPIC_MAPPING.items():
                if event.event_type in types:
                    topic = t
                    break
            else:
                topic = "aegis.events"
        
        # Process directly for demo (no actual Kafka)
        logger.info(f"Publishing event to {topic}: {event.event_type.value}")
        
        # Simulate message
        class MockMessage:
            def __init__(self, value):
                self.value = value
        
        await self._process_message(MockMessage(event.model_dump()))


# =============================================================================
# Event Bus (Singleton)
# =============================================================================

_event_consumer: Optional[KafkaEventConsumer] = None


async def get_event_consumer() -> KafkaEventConsumer:
    """Get or create event consumer."""
    global _event_consumer
    
    if _event_consumer is None:
        _event_consumer = KafkaEventConsumer()
    
    return _event_consumer


async def publish_event(event: HealthcareEvent):
    """Publish event to event bus."""
    consumer = await get_event_consumer()
    await consumer.publish_event(event)


# =============================================================================
# API Router
# =============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/events", tags=["Event Bus"])


class PublishEventRequest(PydanticBaseModel):
    """Request to publish an event."""
    event_type: str
    tenant_id: str = "default"
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/publish")
async def publish_healthcare_event(request: PublishEventRequest):
    """
    Publish a healthcare event to the event bus.
    
    Event will be processed by registered handlers.
    """
    import uuid
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}. Valid types: {[e.value for e in EventType]}"
        )
    
    event = HealthcareEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        tenant_id=request.tenant_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        payload=request.payload,
    )
    
    await publish_event(event)
    
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "status": "published",
    }


@router.get("/types")
async def get_event_types():
    """Get all available event types."""
    return {
        "event_types": [
            {"value": e.value, "name": e.name}
            for e in EventType
        ],
        "topics": KafkaEventConsumer.TOPIC_MAPPING,
    }


@router.get("/handlers")
async def get_event_handlers():
    """Get registered event handlers."""
    consumer = await get_event_consumer()
    
    return {
        "handlers": [
            {
                "name": h.name,
                "event_types": [e.value for e in h.event_types],
            }
            for h in consumer._handlers
        ],
    }


@router.post("/simulate/{event_type}")
async def simulate_event(
    event_type: str,
    patient_id: str = "patient-001",
    tenant_id: str = "default",
):
    """
    Simulate an event for testing.
    
    Useful for demonstrating event-driven processing.
    """
    import uuid
    
    try:
        et = EventType(event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
    
    # Create sample payload based on event type
    payload = {}
    
    if et == EventType.LAB_RESULT_CRITICAL:
        payload = {
            "test_code": "2160-0",
            "test_name": "Creatinine",
            "value": 4.5,
            "unit": "mg/dL",
            "reference_high": 1.3,
            "interpretation": "critical_high",
        }
    elif et == EventType.CLAIM_SUBMITTED:
        payload = {
            "claim": {
                "id": f"claim-{uuid.uuid4().hex[:8]}",
                "claim_type": "professional",
                "total_charge": 5500,
                "diagnoses": ["M54.5", "G89.29"],
            }
        }
    elif et == EventType.PATIENT_DISCHARGED:
        payload = {
            "encounter": {
                "encounter_type": "inpatient",
                "length_of_stay": 5,
                "emergency_admission": True,
            }
        }
    
    event = HealthcareEvent(
        event_id=str(uuid.uuid4()),
        event_type=et,
        tenant_id=tenant_id,
        patient_id=patient_id,
        source_system="simulation",
        payload=payload,
    )
    
    # Process event
    await publish_event(event)
    
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "patient_id": patient_id,
        "payload": payload,
        "status": "processed",
    }
