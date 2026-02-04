"""
AEGIS FHIR Subscriptions

Manage FHIR R5/R4B Subscriptions for real-time notifications.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from enum import Enum
import uuid
import structlog

logger = structlog.get_logger(__name__)


class SubscriptionStatus(str, Enum):
    """FHIR Subscription status."""
    REQUESTED = "requested"
    ACTIVE = "active"
    ERROR = "error"
    OFF = "off"


class SubscriptionChannelType(str, Enum):
    """Subscription channel types."""
    REST_HOOK = "rest-hook"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    MESSAGE = "message"


@dataclass
class SubscriptionCriteria:
    """Criteria for subscription matching."""
    resource_type: str
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubscriptionChannel:
    """Channel configuration for notifications."""
    type: SubscriptionChannelType
    endpoint: str
    headers: dict[str, str] = field(default_factory=dict)
    payload: str = "full-resource"


@dataclass
class FHIRSubscription:
    """A FHIR Subscription resource."""
    id: str
    status: SubscriptionStatus
    criteria: SubscriptionCriteria
    channel: SubscriptionChannel
    reason: str = ""
    tenant_id: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: datetime | None = None
    error_message: str | None = None


class FHIRSubscriptionManager:
    """
    Manages FHIR Subscriptions for real-time notifications.
    
    Features:
    - Create/update/delete subscriptions
    - Match resources against criteria
    - Deliver notifications via webhooks
    - Track subscription status
    """
    
    def __init__(
        self,
        webhook_callback: Callable[[str, dict], Coroutine[Any, Any, bool]] | None = None,
    ):
        self.webhook_callback = webhook_callback
        self._subscriptions: dict[str, FHIRSubscription] = {}
    
    def create_subscription(
        self,
        resource_type: str,
        endpoint: str,
        filters: dict | None = None,
        channel_type: SubscriptionChannelType = SubscriptionChannelType.REST_HOOK,
        headers: dict | None = None,
        reason: str = "",
        tenant_id: str = "default",
    ) -> FHIRSubscription:
        """Create a new FHIR subscription."""
        sub_id = str(uuid.uuid4())
        
        subscription = FHIRSubscription(
            id=sub_id,
            status=SubscriptionStatus.REQUESTED,
            criteria=SubscriptionCriteria(
                resource_type=resource_type,
                filters=filters or {},
            ),
            channel=SubscriptionChannel(
                type=channel_type,
                endpoint=endpoint,
                headers=headers or {},
            ),
            reason=reason,
            tenant_id=tenant_id,
        )
        
        self._subscriptions[sub_id] = subscription
        subscription.status = SubscriptionStatus.ACTIVE
        
        logger.info("Created FHIR subscription", id=sub_id, resource_type=resource_type)
        return subscription
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False
    
    def get_subscription(self, subscription_id: str) -> FHIRSubscription | None:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def list_subscriptions(
        self,
        tenant_id: str | None = None,
        status: SubscriptionStatus | None = None,
    ) -> list[FHIRSubscription]:
        """List subscriptions."""
        subs = list(self._subscriptions.values())
        if tenant_id:
            subs = [s for s in subs if s.tenant_id == tenant_id]
        if status:
            subs = [s for s in subs if s.status == status]
        return subs
    
    async def process_resource(self, resource: dict, tenant_id: str = "default") -> int:
        """Process a resource and notify matching subscriptions."""
        resource_type = resource.get("resourceType")
        if not resource_type:
            return 0
        
        notified = 0
        
        for sub in self._subscriptions.values():
            if sub.status != SubscriptionStatus.ACTIVE:
                continue
            if sub.tenant_id != tenant_id:
                continue
            if sub.criteria.resource_type != resource_type:
                continue
            
            # Check filters
            if self._matches_filters(resource, sub.criteria.filters):
                success = await self._send_notification(sub, resource)
                if success:
                    sub.last_triggered = datetime.now(timezone.utc)
                    notified += 1
        
        return notified
    
    def _matches_filters(self, resource: dict, filters: dict) -> bool:
        """Check if resource matches subscription filters."""
        for key, value in filters.items():
            resource_value = resource.get(key)
            if resource_value != value:
                return False
        return True
    
    async def _send_notification(self, sub: FHIRSubscription, resource: dict) -> bool:
        """Send notification for a subscription."""
        try:
            if self.webhook_callback:
                return await self.webhook_callback(sub.channel.endpoint, resource)
            
            # Default HTTP webhook
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    sub.channel.endpoint,
                    json=resource,
                    headers=sub.channel.headers,
                ) as response:
                    return response.status < 400
        except Exception as e:
            logger.error("Subscription notification failed", id=sub.id, error=str(e))
            sub.error_message = str(e)
            return False
    
    def to_fhir_resource(self, sub: FHIRSubscription) -> dict:
        """Convert to FHIR Subscription resource."""
        return {
            "resourceType": "Subscription",
            "id": sub.id,
            "status": sub.status.value,
            "reason": sub.reason,
            "criteria": f"{sub.criteria.resource_type}?{self._filters_to_query(sub.criteria.filters)}",
            "channel": {
                "type": sub.channel.type.value,
                "endpoint": sub.channel.endpoint,
                "payload": sub.channel.payload,
                "header": [f"{k}: {v}" for k, v in sub.channel.headers.items()],
            },
        }
    
    def _filters_to_query(self, filters: dict) -> str:
        """Convert filters dict to query string."""
        return "&".join(f"{k}={v}" for k, v in filters.items())


_subscription_manager: FHIRSubscriptionManager | None = None


def get_subscription_manager() -> FHIRSubscriptionManager:
    """Get the global subscription manager."""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = FHIRSubscriptionManager()
    return _subscription_manager
