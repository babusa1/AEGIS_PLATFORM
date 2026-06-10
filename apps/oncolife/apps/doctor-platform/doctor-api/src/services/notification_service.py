"""
Notification Service for OncoLife Doctor API.

This service handles sending notifications via:
- Slack webhooks (for team alerts)
- AWS SNS (for email/SMS)
- CloudWatch metrics (for dashboards)

See patient-api notification_service.py for full documentation.
This is a lighter version for the doctor API.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import httpx
import boto3
from botocore.exceptions import ClientError

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SlackNotifier:
    """Send notifications to Slack via webhooks."""
    
    SEVERITY_COLORS = {
        AlertSeverity.INFO: "#36a64f",
        AlertSeverity.WARNING: "#f2c744",
        AlertSeverity.ERROR: "#e01e5a",
        AlertSeverity.CRITICAL: "#8b0000",
    }
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or getattr(settings, 'slack_webhook_url', None)
        self.service_name = settings.app_name
        self.environment = settings.environment
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an alert to Slack."""
        if not self.webhook_url:
            return False
        
        payload = {
            "attachments": [{
                "color": self.SEVERITY_COLORS[severity],
                "title": f"[{severity.value.upper()}] {title}",
                "text": message,
                "fields": [
                    {"title": "Service", "value": self.service_name, "short": True},
                    {"title": "Environment", "value": self.environment, "short": True},
                ],
                "footer": f"OncoLife Doctor API | {datetime.utcnow().isoformat()}Z"
            }]
        }
        
        if details:
            for key, value in list(details.items())[:5]:
                payload["attachments"][0]["fields"].append({
                    "title": key, "value": str(value), "short": True
                })
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class CloudWatchMetrics:
    """Send custom metrics to CloudWatch."""
    
    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or getattr(settings, 'cloudwatch_namespace', 'OncoLife/DoctorAPI')
        self.client = boto3.client('cloudwatch', region_name=getattr(settings, 'aws_region', 'eu-west-2'))
        self.environment = settings.environment
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Put a custom metric to CloudWatch."""
        metric_dimensions = [{'Name': 'Environment', 'Value': self.environment}]
        
        if dimensions:
            for name, value_str in dimensions.items():
                metric_dimensions.append({'Name': name, 'Value': value_str})
        
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    'MetricName': metric_name,
                    'Dimensions': metric_dimensions,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }]
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to put CloudWatch metric: {e}")
            return False
    
    def increment_counter(self, metric_name: str, dimensions: Optional[Dict[str, str]] = None) -> bool:
        return self.put_metric(metric_name, 1.0, "Count", dimensions)


class NotificationService:
    """Unified notification service for Doctor API."""
    
    def __init__(self):
        self.slack = SlackNotifier()
        self.cloudwatch = CloudWatchMetrics()
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """Send an alert to appropriate channels."""
        results = {}
        
        if severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            results["slack"] = await self.slack.send_alert(title, message, severity, details)
        
        results["cloudwatch"] = self.cloudwatch.increment_counter(
            f"Alert_{severity.value.capitalize()}",
            {"AlertType": title.replace(" ", "_")[:50]}
        )
        
        return results


# Singleton
_notification_service: Optional[NotificationService] = None

def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


__all__ = [
    "NotificationService",
    "get_notification_service",
    "AlertSeverity",
    "SlackNotifier",
    "CloudWatchMetrics",
]
