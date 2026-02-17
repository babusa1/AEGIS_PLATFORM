"""
VeritOS Notifications Module

Alert and notification delivery:
- Slack webhooks
- Microsoft Teams
- Email
- Custom webhooks
"""

from aegis.notifications.webhooks import (
    NotificationChannel,
    NotificationPriority,
    AlertType,
    Alert,
    NotificationTarget,
    NotificationResult,
    NotificationService,
    get_notification_service,
    router as notifications_router,
)

__all__ = [
    "NotificationChannel",
    "NotificationPriority",
    "AlertType",
    "Alert",
    "NotificationTarget",
    "NotificationResult",
    "NotificationService",
    "get_notification_service",
    "notifications_router",
]
