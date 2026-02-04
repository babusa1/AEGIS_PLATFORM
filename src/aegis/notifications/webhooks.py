"""
Alert Webhook Notifications

Send alerts to external systems:
- Slack integration
- Microsoft Teams
- Email notifications
- Custom webhooks
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import json

import structlog
from pydantic import BaseModel, Field
import httpx

logger = structlog.get_logger(__name__)


# =============================================================================
# Notification Types
# =============================================================================

class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class AlertType(str, Enum):
    """Types of alerts."""
    CLINICAL = "clinical"
    DENIAL = "denial"
    READMISSION_RISK = "readmission_risk"
    SYSTEM = "system"
    TRIAGE = "triage"
    CUSTOM = "custom"


# =============================================================================
# Notification Models
# =============================================================================

class NotificationTarget(BaseModel):
    """Target for notification delivery."""
    channel: NotificationChannel
    target_id: str  # Slack channel, email address, webhook URL, etc.
    config: Dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    """Alert to be sent."""
    id: str
    alert_type: AlertType
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Content
    title: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Context
    tenant_id: str = "default"
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    
    # Actions
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class NotificationResult(BaseModel):
    """Result of notification delivery."""
    alert_id: str
    channel: NotificationChannel
    target_id: str
    success: bool
    message: Optional[str] = None
    sent_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Channel Integrations
# =============================================================================

class SlackNotifier:
    """Send notifications to Slack."""
    
    async def send(
        self,
        webhook_url: str,
        alert: Alert,
        config: Dict[str, Any] = None,
    ) -> NotificationResult:
        """Send alert to Slack channel."""
        config = config or {}
        
        # Build Slack message
        color = self._get_color(alert.priority)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{self._get_emoji(alert.priority)} {alert.title}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert.message,
                }
            },
        ]
        
        # Add patient context if available
        if alert.patient_id:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Patient:* {alert.patient_name or alert.patient_id}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:* {alert.priority.value.upper()}",
                    },
                ]
            })
        
        # Add details
        if alert.details:
            detail_text = "\n".join(f"• *{k}:* {v}" for k, v in alert.details.items())
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text,
                }
            })
        
        # Add action button
        if alert.action_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": alert.action_label or "View Details",
                        },
                        "url": alert.action_url,
                    }
                ]
            })
        
        payload = {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "footer": f"AEGIS Alert • {alert.alert_type.value} • {alert.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                
                success = response.status_code == 200
                
                return NotificationResult(
                    alert_id=alert.id,
                    channel=NotificationChannel.SLACK,
                    target_id=webhook_url[:50] + "...",
                    success=success,
                    message="Sent" if success else f"HTTP {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return NotificationResult(
                alert_id=alert.id,
                channel=NotificationChannel.SLACK,
                target_id=webhook_url[:50] + "...",
                success=False,
                message=str(e),
            )
    
    def _get_color(self, priority: NotificationPriority) -> str:
        """Get Slack attachment color for priority."""
        return {
            NotificationPriority.CRITICAL: "#FF0000",
            NotificationPriority.HIGH: "#FFA500",
            NotificationPriority.NORMAL: "#36A64F",
            NotificationPriority.LOW: "#808080",
        }.get(priority, "#36A64F")
    
    def _get_emoji(self, priority: NotificationPriority) -> str:
        """Get emoji for priority."""
        return {
            NotificationPriority.CRITICAL: "🚨",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.NORMAL: "ℹ️",
            NotificationPriority.LOW: "📋",
        }.get(priority, "📋")


class TeamsNotifier:
    """Send notifications to Microsoft Teams."""
    
    async def send(
        self,
        webhook_url: str,
        alert: Alert,
        config: Dict[str, Any] = None,
    ) -> NotificationResult:
        """Send alert to Teams channel."""
        config = config or {}
        
        color = self._get_color(alert.priority)
        
        # Build Teams adaptive card
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color.replace("#", ""),
            "summary": alert.title,
            "sections": [
                {
                    "activityTitle": f"{self._get_emoji(alert.priority)} {alert.title}",
                    "activitySubtitle": f"Priority: {alert.priority.value.upper()}",
                    "text": alert.message,
                    "facts": [],
                }
            ],
        }
        
        # Add facts
        if alert.patient_id:
            card["sections"][0]["facts"].append({
                "name": "Patient",
                "value": alert.patient_name or alert.patient_id,
            })
        
        for key, value in alert.details.items():
            card["sections"][0]["facts"].append({
                "name": key,
                "value": str(value),
            })
        
        # Add action
        if alert.action_url:
            card["potentialAction"] = [
                {
                    "@type": "OpenUri",
                    "name": alert.action_label or "View Details",
                    "targets": [{"os": "default", "uri": alert.action_url}],
                }
            ]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=card,
                    timeout=10.0,
                )
                
                success = response.status_code == 200
                
                return NotificationResult(
                    alert_id=alert.id,
                    channel=NotificationChannel.TEAMS,
                    target_id=webhook_url[:50] + "...",
                    success=success,
                    message="Sent" if success else f"HTTP {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"Teams notification failed: {e}")
            return NotificationResult(
                alert_id=alert.id,
                channel=NotificationChannel.TEAMS,
                target_id=webhook_url[:50] + "...",
                success=False,
                message=str(e),
            )
    
    def _get_color(self, priority: NotificationPriority) -> str:
        """Get color for priority."""
        return {
            NotificationPriority.CRITICAL: "#FF0000",
            NotificationPriority.HIGH: "#FFA500",
            NotificationPriority.NORMAL: "#36A64F",
            NotificationPriority.LOW: "#808080",
        }.get(priority, "#36A64F")
    
    def _get_emoji(self, priority: NotificationPriority) -> str:
        """Get emoji for priority."""
        return {
            NotificationPriority.CRITICAL: "🚨",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.NORMAL: "ℹ️",
            NotificationPriority.LOW: "📋",
        }.get(priority, "📋")


class EmailNotifier:
    """Send notifications via email (SMTP)."""
    
    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        from_address: str = "alerts@aegis-platform.com",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
    
    async def send(
        self,
        to_address: str,
        alert: Alert,
        config: Dict[str, Any] = None,
    ) -> NotificationResult:
        """Send alert via email."""
        # Build email content
        subject = f"[{alert.priority.value.upper()}] {alert.title}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {self._get_color(alert.priority)}; color: white; padding: 10px;">
                <h2>{alert.title}</h2>
            </div>
            <div style="padding: 15px;">
                <p>{alert.message}</p>
                
                {f'<p><strong>Patient:</strong> {alert.patient_name or alert.patient_id}</p>' if alert.patient_id else ''}
                
                <h3>Details</h3>
                <ul>
                    {''.join(f'<li><strong>{k}:</strong> {v}</li>' for k, v in alert.details.items())}
                </ul>
                
                {f'<p><a href="{alert.action_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none;">{alert.action_label or "View Details"}</a></p>' if alert.action_url else ''}
            </div>
            <div style="color: #666; font-size: 12px; padding: 10px; border-top: 1px solid #eee;">
                AEGIS Healthcare Platform • {alert.created_at.strftime('%Y-%m-%d %H:%M UTC')}
            </div>
        </body>
        </html>
        """
        
        try:
            # In production, would use aiosmtplib
            # For demo, just log
            logger.info(
                "Email notification (simulated)",
                to=to_address,
                subject=subject,
            )
            
            return NotificationResult(
                alert_id=alert.id,
                channel=NotificationChannel.EMAIL,
                target_id=to_address,
                success=True,
                message="Sent (simulated)",
            )
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return NotificationResult(
                alert_id=alert.id,
                channel=NotificationChannel.EMAIL,
                target_id=to_address,
                success=False,
                message=str(e),
            )
    
    def _get_color(self, priority: NotificationPriority) -> str:
        """Get color for priority."""
        return {
            NotificationPriority.CRITICAL: "#FF0000",
            NotificationPriority.HIGH: "#FFA500",
            NotificationPriority.NORMAL: "#36A64F",
            NotificationPriority.LOW: "#808080",
        }.get(priority, "#36A64F")


class WebhookNotifier:
    """Send notifications to custom webhooks."""
    
    async def send(
        self,
        webhook_url: str,
        alert: Alert,
        config: Dict[str, Any] = None,
    ) -> NotificationResult:
        """Send alert to custom webhook."""
        config = config or {}
        
        # Build payload
        payload = {
            "alert_id": alert.id,
            "alert_type": alert.alert_type.value,
            "priority": alert.priority.value,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details,
            "patient_id": alert.patient_id,
            "patient_name": alert.patient_name,
            "action_url": alert.action_url,
            "created_at": alert.created_at.isoformat(),
            "tenant_id": alert.tenant_id,
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AEGIS-Platform/1.0",
        }
        
        # Add custom headers from config
        if "headers" in config:
            headers.update(config["headers"])
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=config.get("timeout", 10.0),
                )
                
                success = 200 <= response.status_code < 300
                
                return NotificationResult(
                    alert_id=alert.id,
                    channel=NotificationChannel.WEBHOOK,
                    target_id=webhook_url[:50] + "...",
                    success=success,
                    message=f"HTTP {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return NotificationResult(
                alert_id=alert.id,
                channel=NotificationChannel.WEBHOOK,
                target_id=webhook_url[:50] + "...",
                success=False,
                message=str(e),
            )


# =============================================================================
# Notification Service
# =============================================================================

class NotificationService:
    """
    Central notification service.
    
    Manages alert delivery to multiple channels.
    """
    
    def __init__(self):
        self._slack = SlackNotifier()
        self._teams = TeamsNotifier()
        self._email = EmailNotifier()
        self._webhook = WebhookNotifier()
        
        # Configured targets
        self._targets: List[NotificationTarget] = []
    
    def configure_target(self, target: NotificationTarget):
        """Add a notification target."""
        self._targets.append(target)
        logger.info(f"Configured notification target: {target.channel.value}")
    
    async def send_alert(
        self,
        alert: Alert,
        channels: List[NotificationChannel] = None,
    ) -> List[NotificationResult]:
        """
        Send alert to configured channels.
        
        Args:
            alert: Alert to send
            channels: Specific channels (all configured if not specified)
            
        Returns:
            List of notification results
        """
        results = []
        
        for target in self._targets:
            if channels and target.channel not in channels:
                continue
            
            result = await self._send_to_target(alert, target)
            results.append(result)
        
        # Log results
        success_count = sum(1 for r in results if r.success)
        logger.info(
            "Alert sent",
            alert_id=alert.id,
            alert_type=alert.alert_type.value,
            success=success_count,
            total=len(results),
        )
        
        return results
    
    async def _send_to_target(
        self,
        alert: Alert,
        target: NotificationTarget,
    ) -> NotificationResult:
        """Send alert to specific target."""
        if target.channel == NotificationChannel.SLACK:
            return await self._slack.send(
                target.target_id,
                alert,
                target.config,
            )
        
        elif target.channel == NotificationChannel.TEAMS:
            return await self._teams.send(
                target.target_id,
                alert,
                target.config,
            )
        
        elif target.channel == NotificationChannel.EMAIL:
            return await self._email.send(
                target.target_id,
                alert,
                target.config,
            )
        
        elif target.channel == NotificationChannel.WEBHOOK:
            return await self._webhook.send(
                target.target_id,
                alert,
                target.config,
            )
        
        else:
            return NotificationResult(
                alert_id=alert.id,
                channel=target.channel,
                target_id=target.target_id,
                success=False,
                message=f"Unsupported channel: {target.channel}",
            )


# Global service
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


# =============================================================================
# API Router
# =============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class ConfigureTargetRequest(PydanticBaseModel):
    """Request to configure notification target."""
    channel: NotificationChannel
    target_id: str
    config: Dict[str, Any] = Field(default_factory=dict)


class SendAlertRequest(PydanticBaseModel):
    """Request to send an alert."""
    alert_type: AlertType = AlertType.CUSTOM
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    channels: Optional[List[NotificationChannel]] = None


class TestNotificationRequest(PydanticBaseModel):
    """Request to test a notification channel."""
    channel: NotificationChannel
    target_id: str
    config: Dict[str, Any] = Field(default_factory=dict)


@router.post("/targets")
async def configure_notification_target(request: ConfigureTargetRequest):
    """
    Configure a notification target.
    
    Adds a destination for alert delivery.
    """
    service = get_notification_service()
    
    target = NotificationTarget(
        channel=request.channel,
        target_id=request.target_id,
        config=request.config,
    )
    
    service.configure_target(target)
    
    return {
        "status": "configured",
        "channel": request.channel.value,
        "target_id": request.target_id[:50] + "..." if len(request.target_id) > 50 else request.target_id,
    }


@router.get("/targets")
async def get_notification_targets():
    """Get configured notification targets."""
    service = get_notification_service()
    
    return {
        "targets": [
            {
                "channel": t.channel.value,
                "target_id": t.target_id[:50] + "..." if len(t.target_id) > 50 else t.target_id,
            }
            for t in service._targets
        ],
    }


@router.post("/send")
async def send_alert(request: SendAlertRequest):
    """
    Send an alert to configured channels.
    
    Delivers notification to all configured targets
    (or specific channels if specified).
    """
    import uuid
    
    service = get_notification_service()
    
    if not service._targets:
        raise HTTPException(
            status_code=400,
            detail="No notification targets configured. Use POST /notifications/targets first.",
        )
    
    alert = Alert(
        id=str(uuid.uuid4()),
        alert_type=request.alert_type,
        priority=request.priority,
        title=request.title,
        message=request.message,
        details=request.details,
        patient_id=request.patient_id,
        patient_name=request.patient_name,
        action_url=request.action_url,
        action_label=request.action_label,
    )
    
    results = await service.send_alert(alert, request.channels)
    
    return {
        "alert_id": alert.id,
        "results": [
            {
                "channel": r.channel.value,
                "success": r.success,
                "message": r.message,
            }
            for r in results
        ],
        "success_count": sum(1 for r in results if r.success),
        "total": len(results),
    }


@router.post("/test")
async def test_notification(request: TestNotificationRequest):
    """
    Send a test notification to verify configuration.
    
    Useful for validating webhook URLs and credentials.
    """
    import uuid
    
    alert = Alert(
        id=str(uuid.uuid4()),
        alert_type=AlertType.SYSTEM,
        priority=NotificationPriority.LOW,
        title="AEGIS Test Notification",
        message="This is a test notification from AEGIS Healthcare Platform. If you received this, your notification channel is configured correctly!",
        details={
            "test": True,
            "channel": request.channel.value,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    
    # Send directly to the specified target
    service = get_notification_service()
    
    target = NotificationTarget(
        channel=request.channel,
        target_id=request.target_id,
        config=request.config,
    )
    
    result = await service._send_to_target(alert, target)
    
    return {
        "test_id": alert.id,
        "channel": request.channel.value,
        "success": result.success,
        "message": result.message,
    }


@router.get("/channels")
async def get_available_channels():
    """Get available notification channels."""
    return {
        "channels": [
            {
                "id": c.value,
                "name": c.name,
                "description": {
                    NotificationChannel.SLACK: "Slack webhook integration",
                    NotificationChannel.TEAMS: "Microsoft Teams webhook",
                    NotificationChannel.EMAIL: "SMTP email delivery",
                    NotificationChannel.WEBHOOK: "Custom HTTP webhook",
                    NotificationChannel.SMS: "SMS text messages",
                }.get(c, ""),
            }
            for c in NotificationChannel
        ],
    }
