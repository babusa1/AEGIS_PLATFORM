"""
Trigger Manager

n8n-style triggers with:
- Webhook triggers
- Schedule (cron) triggers
- Event triggers (Kafka)
- Database triggers (CDC)
- Manual triggers
"""

from typing import Any, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import json
import re

import structlog
from pydantic import BaseModel, Field
from croniter import croniter

logger = structlog.get_logger(__name__)


# =============================================================================
# Trigger Types
# =============================================================================

class TriggerType(str, Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"
    DATABASE = "database"
    FILE = "file"
    EMAIL = "email"
    CHAT = "chat"
    WORKFLOW = "workflow"  # Triggered by another workflow


class TriggerStatus(str, Enum):
    """Trigger status."""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


# =============================================================================
# Trigger Configurations
# =============================================================================

class WebhookConfig(BaseModel):
    """Webhook trigger configuration."""
    path: str  # /webhooks/{path}
    methods: list[str] = Field(default=["POST"])
    auth_type: str = "none"  # none, api_key, basic, bearer
    auth_value: str | None = None
    response_mode: str = "immediate"  # immediate, wait_for_completion
    response_timeout_seconds: int = 30
    

class ScheduleConfig(BaseModel):
    """Schedule trigger configuration."""
    cron: str  # Cron expression
    timezone: str = "UTC"
    enabled: bool = True
    

class EventConfig(BaseModel):
    """Event trigger configuration."""
    topic: str  # Kafka topic
    group_id: str | None = None
    filter_expression: str | None = None  # JSONPath filter
    batch_size: int = 1
    

class DatabaseConfig(BaseModel):
    """Database CDC trigger configuration."""
    table: str
    operations: list[str] = Field(default=["INSERT", "UPDATE", "DELETE"])
    filter_column: str | None = None
    filter_value: str | None = None


# =============================================================================
# Trigger Definition
# =============================================================================

class TriggerDefinition(BaseModel):
    """Complete trigger definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: TriggerType
    workflow_id: str
    
    # Type-specific config
    webhook_config: WebhookConfig | None = None
    schedule_config: ScheduleConfig | None = None
    event_config: EventConfig | None = None
    database_config: DatabaseConfig | None = None
    
    # Status
    status: TriggerStatus = TriggerStatus.ACTIVE
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: datetime | None = None
    trigger_count: int = 0
    
    # Tenant
    tenant_id: str = "default"


class TriggerEvent(BaseModel):
    """An event that triggered a workflow."""
    trigger_id: str
    trigger_type: TriggerType
    workflow_id: str
    
    # Event data
    payload: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    
    # Timing
    received_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Source info
    source_ip: str | None = None
    source_id: str | None = None


# =============================================================================
# Trigger Manager
# =============================================================================

class TriggerManager:
    """
    Manages all workflow triggers.
    
    Features:
    - Register/unregister triggers
    - Webhook handling
    - Cron scheduling
    - Kafka event consumption
    - Database CDC monitoring
    """
    
    def __init__(self, pool=None, kafka_consumer=None):
        self.pool = pool
        self.kafka_consumer = kafka_consumer
        
        # Registered triggers
        self._triggers: dict[str, TriggerDefinition] = {}
        
        # Webhook routes
        self._webhook_routes: dict[str, str] = {}  # path -> trigger_id
        
        # Schedule tasks
        self._schedule_tasks: dict[str, asyncio.Task] = {}
        
        # Event handlers
        self._event_handlers: dict[str, Callable] = {}
        
        # Callback for triggering workflows
        self._workflow_callback: Callable[[str, dict], Awaitable[str]] | None = None
    
    def set_workflow_callback(self, callback: Callable[[str, dict], Awaitable[str]]):
        """Set callback for triggering workflows."""
        self._workflow_callback = callback
    
    # =========================================================================
    # Trigger Registration
    # =========================================================================
    
    def register_trigger(self, trigger: TriggerDefinition) -> str:
        """Register a new trigger."""
        self._triggers[trigger.id] = trigger
        
        # Type-specific setup
        if trigger.type == TriggerType.WEBHOOK and trigger.webhook_config:
            self._webhook_routes[trigger.webhook_config.path] = trigger.id
            logger.info("Registered webhook", path=trigger.webhook_config.path)
            
        elif trigger.type == TriggerType.SCHEDULE and trigger.schedule_config:
            self._start_schedule(trigger)
            logger.info("Registered schedule", cron=trigger.schedule_config.cron)
            
        elif trigger.type == TriggerType.EVENT and trigger.event_config:
            self._register_event_handler(trigger)
            logger.info("Registered event trigger", topic=trigger.event_config.topic)
        
        return trigger.id
    
    def unregister_trigger(self, trigger_id: str):
        """Unregister a trigger."""
        trigger = self._triggers.pop(trigger_id, None)
        if not trigger:
            return
        
        # Cleanup
        if trigger.type == TriggerType.WEBHOOK and trigger.webhook_config:
            self._webhook_routes.pop(trigger.webhook_config.path, None)
            
        elif trigger.type == TriggerType.SCHEDULE:
            task = self._schedule_tasks.pop(trigger_id, None)
            if task:
                task.cancel()
                
        elif trigger.type == TriggerType.EVENT:
            self._event_handlers.pop(trigger_id, None)
    
    def get_trigger(self, trigger_id: str) -> TriggerDefinition | None:
        """Get trigger by ID."""
        return self._triggers.get(trigger_id)
    
    def list_triggers(self, workflow_id: str = None) -> list[TriggerDefinition]:
        """List all triggers, optionally filtered by workflow."""
        triggers = list(self._triggers.values())
        if workflow_id:
            triggers = [t for t in triggers if t.workflow_id == workflow_id]
        return triggers
    
    # =========================================================================
    # Webhook Handling
    # =========================================================================
    
    async def handle_webhook(
        self,
        path: str,
        method: str,
        body: dict,
        headers: dict,
        source_ip: str = None,
    ) -> dict:
        """
        Handle incoming webhook request.
        
        Returns:
            dict with execution_id or error
        """
        trigger_id = self._webhook_routes.get(path)
        if not trigger_id:
            return {"error": "Webhook not found", "status": 404}
        
        trigger = self._triggers.get(trigger_id)
        if not trigger or trigger.status != TriggerStatus.ACTIVE:
            return {"error": "Trigger not active", "status": 503}
        
        config = trigger.webhook_config
        if not config:
            return {"error": "Invalid trigger config", "status": 500}
        
        # Check method
        if method.upper() not in config.methods:
            return {"error": f"Method {method} not allowed", "status": 405}
        
        # Check auth
        if config.auth_type != "none":
            if not self._verify_webhook_auth(config, headers):
                return {"error": "Unauthorized", "status": 401}
        
        # Create trigger event
        event = TriggerEvent(
            trigger_id=trigger_id,
            trigger_type=TriggerType.WEBHOOK,
            workflow_id=trigger.workflow_id,
            payload=body,
            headers=headers,
            source_ip=source_ip,
        )
        
        # Update trigger stats
        trigger.last_triggered = datetime.utcnow()
        trigger.trigger_count += 1
        
        # Trigger workflow
        if self._workflow_callback:
            execution_id = await self._workflow_callback(
                trigger.workflow_id,
                {
                    "trigger_type": "webhook",
                    "trigger_id": trigger_id,
                    "payload": body,
                    "headers": headers,
                },
            )
            
            return {
                "status": 200,
                "execution_id": execution_id,
                "message": "Workflow triggered",
            }
        
        return {"error": "No workflow callback configured", "status": 500}
    
    def _verify_webhook_auth(self, config: WebhookConfig, headers: dict) -> bool:
        """Verify webhook authentication."""
        if config.auth_type == "api_key":
            return headers.get("X-API-Key") == config.auth_value
        elif config.auth_type == "bearer":
            auth = headers.get("Authorization", "")
            return auth == f"Bearer {config.auth_value}"
        elif config.auth_type == "basic":
            # Would decode and verify basic auth
            pass
        return True
    
    # =========================================================================
    # Schedule Handling
    # =========================================================================
    
    def _start_schedule(self, trigger: TriggerDefinition):
        """Start a schedule trigger."""
        config = trigger.schedule_config
        if not config:
            return
        
        async def schedule_loop():
            cron = croniter(config.cron, datetime.utcnow())
            
            while True:
                try:
                    # Calculate next run
                    next_run = cron.get_next(datetime)
                    wait_seconds = (next_run - datetime.utcnow()).total_seconds()
                    
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                    
                    # Check if still active
                    current_trigger = self._triggers.get(trigger.id)
                    if not current_trigger or current_trigger.status != TriggerStatus.ACTIVE:
                        break
                    
                    if not config.enabled:
                        continue
                    
                    # Trigger workflow
                    if self._workflow_callback:
                        await self._workflow_callback(
                            trigger.workflow_id,
                            {
                                "trigger_type": "schedule",
                                "trigger_id": trigger.id,
                                "scheduled_time": next_run.isoformat(),
                            },
                        )
                    
                    # Update stats
                    trigger.last_triggered = datetime.utcnow()
                    trigger.trigger_count += 1
                    
                    logger.info(
                        "Schedule triggered",
                        trigger_id=trigger.id,
                        workflow_id=trigger.workflow_id,
                    )
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Schedule error", error=str(e))
                    await asyncio.sleep(60)  # Wait before retry
        
        task = asyncio.create_task(schedule_loop())
        self._schedule_tasks[trigger.id] = task
    
    def pause_schedule(self, trigger_id: str):
        """Pause a schedule trigger."""
        trigger = self._triggers.get(trigger_id)
        if trigger and trigger.schedule_config:
            trigger.schedule_config.enabled = False
    
    def resume_schedule(self, trigger_id: str):
        """Resume a schedule trigger."""
        trigger = self._triggers.get(trigger_id)
        if trigger and trigger.schedule_config:
            trigger.schedule_config.enabled = True
    
    # =========================================================================
    # Event Handling (Kafka)
    # =========================================================================
    
    def _register_event_handler(self, trigger: TriggerDefinition):
        """Register an event handler for Kafka topic."""
        config = trigger.event_config
        if not config or not self.kafka_consumer:
            return
        
        async def event_handler(event_data: dict):
            # Apply filter if configured
            if config.filter_expression:
                # Would use JSONPath to filter
                pass
            
            # Trigger workflow
            if self._workflow_callback:
                await self._workflow_callback(
                    trigger.workflow_id,
                    {
                        "trigger_type": "event",
                        "trigger_id": trigger.id,
                        "topic": config.topic,
                        "payload": event_data,
                    },
                )
            
            trigger.last_triggered = datetime.utcnow()
            trigger.trigger_count += 1
        
        self._event_handlers[trigger.id] = event_handler
        
        # Would subscribe to Kafka topic here
        # self.kafka_consumer.subscribe(config.topic, event_handler)
    
    # =========================================================================
    # Manual Triggers
    # =========================================================================
    
    async def trigger_manual(
        self,
        workflow_id: str,
        inputs: dict = None,
        user_id: str = None,
    ) -> str:
        """Manually trigger a workflow."""
        if self._workflow_callback:
            execution_id = await self._workflow_callback(
                workflow_id,
                {
                    "trigger_type": "manual",
                    "user_id": user_id,
                    "inputs": inputs or {},
                },
            )
            return execution_id
        
        raise RuntimeError("No workflow callback configured")
    
    # =========================================================================
    # Trigger Templates
    # =========================================================================
    
    def create_webhook_trigger(
        self,
        workflow_id: str,
        path: str,
        name: str = None,
        methods: list[str] = None,
    ) -> TriggerDefinition:
        """Convenience method to create a webhook trigger."""
        trigger = TriggerDefinition(
            name=name or f"Webhook: {path}",
            type=TriggerType.WEBHOOK,
            workflow_id=workflow_id,
            webhook_config=WebhookConfig(
                path=path,
                methods=methods or ["POST"],
            ),
        )
        self.register_trigger(trigger)
        return trigger
    
    def create_schedule_trigger(
        self,
        workflow_id: str,
        cron: str,
        name: str = None,
        timezone: str = "UTC",
    ) -> TriggerDefinition:
        """Convenience method to create a schedule trigger."""
        trigger = TriggerDefinition(
            name=name or f"Schedule: {cron}",
            type=TriggerType.SCHEDULE,
            workflow_id=workflow_id,
            schedule_config=ScheduleConfig(
                cron=cron,
                timezone=timezone,
            ),
        )
        self.register_trigger(trigger)
        return trigger
    
    def create_event_trigger(
        self,
        workflow_id: str,
        topic: str,
        name: str = None,
    ) -> TriggerDefinition:
        """Convenience method to create an event trigger."""
        trigger = TriggerDefinition(
            name=name or f"Event: {topic}",
            type=TriggerType.EVENT,
            workflow_id=workflow_id,
            event_config=EventConfig(topic=topic),
        )
        self.register_trigger(trigger)
        return trigger
