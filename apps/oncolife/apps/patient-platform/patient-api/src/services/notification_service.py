"""
Notification Service for OncoLife Patient API.

This service handles sending notifications via:
- Slack webhooks (for team alerts)
- AWS SNS (for email/SMS)
- CloudWatch metrics (for dashboards)

Used for:
- Application errors and exceptions
- Health check failures
- Security alerts (rate limiting, auth failures)
- Business metrics

Configuration:
    Set the following environment variables:
    - SLACK_WEBHOOK_URL: Slack incoming webhook URL
    - SNS_ALERT_TOPIC_ARN: AWS SNS topic for email/SMS alerts
    - CLOUDWATCH_NAMESPACE: Custom CloudWatch namespace
"""

import json
import time
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


class NotificationChannel(Enum):
    """Available notification channels."""
    SLACK = "slack"
    EMAIL = "email"  # via SNS
    SMS = "sms"  # via SNS
    CLOUDWATCH = "cloudwatch"


# =============================================================================
# SLACK NOTIFICATIONS
# =============================================================================

class SlackNotifier:
    """
    Send notifications to Slack via webhooks.
    
    Formats messages with rich attachments including:
    - Severity-colored sidebar
    - Environment and service info
    - Error details and stack traces
    - Action buttons for quick access
    """
    
    SEVERITY_COLORS = {
        AlertSeverity.INFO: "#36a64f",      # Green
        AlertSeverity.WARNING: "#f2c744",   # Yellow
        AlertSeverity.ERROR: "#e01e5a",     # Red
        AlertSeverity.CRITICAL: "#8b0000",  # Dark Red
    }
    
    SEVERITY_EMOJIS = {
        AlertSeverity.INFO: ":information_source:",
        AlertSeverity.WARNING: ":warning:",
        AlertSeverity.ERROR: ":x:",
        AlertSeverity.CRITICAL: ":rotating_light:",
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
        error: Optional[Exception] = None,
    ) -> bool:
        """
        Send an alert to Slack.
        
        Args:
            title: Alert title
            message: Alert description
            severity: Alert severity level
            details: Additional context (request info, metrics, etc.)
            error: Exception object if applicable
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug("Slack webhook URL not configured, skipping notification")
            return False
        
        emoji = self.SEVERITY_EMOJIS[severity]
        color = self.SEVERITY_COLORS[severity]
        
        # Build the Slack message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Service:* {self.service_name} | *Environment:* {self.environment} | *Time:* {datetime.utcnow().isoformat()}Z"
                    }
                ]
            }
        ]
        
        # Add details if provided
        if details:
            fields = []
            for key, value in details.items():
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })
            
            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields[:10]  # Slack limits to 10 fields
                })
        
        # Add error traceback if provided
        if error:
            import traceback
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            error_text = "".join(tb)[-2000:]  # Limit size
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{error_text}```"
                }
            })
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info(f"Slack notification sent: {title}")
                    return True
                else:
                    logger.error(f"Slack notification failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


# =============================================================================
# AWS SNS NOTIFICATIONS (Email/SMS)
# =============================================================================

class SNSNotifier:
    """
    Send notifications via AWS SNS for email and SMS.
    
    Prerequisites:
    - SNS topic created with email/SMS subscriptions
    - IAM role with sns:Publish permission
    """
    
    def __init__(self, topic_arn: Optional[str] = None):
        self.topic_arn = topic_arn or getattr(settings, 'sns_alert_topic_arn', None)
        self.client = boto3.client('sns', region_name=getattr(settings, 'aws_region', 'eu-west-2'))
        self.service_name = settings.app_name
        self.environment = settings.environment
    
    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an alert via SNS.
        
        Args:
            title: Alert title (used as email subject)
            message: Alert description
            severity: Alert severity level
            details: Additional context
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.topic_arn:
            logger.debug("SNS topic ARN not configured, skipping notification")
            return False
        
        # Build the message
        full_message = f"""
[{severity.value.upper()}] {title}

Service: {self.service_name}
Environment: {self.environment}
Time: {datetime.utcnow().isoformat()}Z

Message:
{message}
"""
        
        if details:
            full_message += "\nDetails:\n"
            for key, value in details.items():
                full_message += f"  - {key}: {value}\n"
        
        try:
            response = self.client.publish(
                TopicArn=self.topic_arn,
                Subject=f"[{self.environment.upper()}] {severity.value.upper()}: {title}"[:100],
                Message=full_message,
                MessageAttributes={
                    'severity': {
                        'DataType': 'String',
                        'StringValue': severity.value
                    },
                    'service': {
                        'DataType': 'String',
                        'StringValue': self.service_name
                    },
                    'environment': {
                        'DataType': 'String',
                        'StringValue': self.environment
                    }
                }
            )
            
            logger.info(f"SNS notification sent: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to send SNS notification: {e}")
            return False


# =============================================================================
# CLOUDWATCH METRICS
# =============================================================================

class CloudWatchMetrics:
    """
    Send custom metrics to CloudWatch for dashboards and alarms.
    
    Metrics:
    - API error counts by type
    - Authentication failures
    - Rate limit hits
    - Database connection failures
    - Response latencies
    """
    
    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or getattr(settings, 'cloudwatch_namespace', 'OncoLife/PatientAPI')
        self.client = boto3.client('cloudwatch', region_name=getattr(settings, 'aws_region', 'eu-west-2'))
        self.environment = settings.environment
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Put a custom metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit type (Count, Seconds, Milliseconds, etc.)
            dimensions: Additional dimensions for the metric
        
        Returns:
            True if sent successfully, False otherwise
        """
        metric_dimensions = [
            {'Name': 'Environment', 'Value': self.environment},
        ]
        
        if dimensions:
            for name, value_str in dimensions.items():
                metric_dimensions.append({'Name': name, 'Value': value_str})
        
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Dimensions': metric_dimensions,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to put CloudWatch metric: {e}")
            return False
    
    def increment_counter(
        self,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Increment a counter metric by 1."""
        return self.put_metric(metric_name, 1.0, "Count", dimensions)
    
    def record_latency(
        self,
        metric_name: str,
        latency_ms: float,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Record a latency metric in milliseconds."""
        return self.put_metric(metric_name, latency_ms, "Milliseconds", dimensions)


# =============================================================================
# UNIFIED NOTIFICATION SERVICE
# =============================================================================

class NotificationService:
    """
    Unified notification service that routes alerts to appropriate channels.
    
    Channel selection based on severity:
    - CRITICAL: Slack + SNS (Email/SMS) + CloudWatch
    - ERROR: Slack + CloudWatch
    - WARNING: Slack (optional) + CloudWatch
    - INFO: CloudWatch only
    
    Usage:
        notification_service = NotificationService()
        
        await notification_service.send_alert(
            title="Database Connection Failed",
            message="Unable to connect to patient database",
            severity=AlertSeverity.CRITICAL,
            details={"host": "db.example.com", "port": 5432}
        )
    """
    
    def __init__(self):
        self.slack = SlackNotifier()
        self.sns = SNSNotifier()
        self.cloudwatch = CloudWatchMetrics()
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> Dict[str, bool]:
        """
        Send an alert to appropriate notification channels.
        
        Args:
            title: Alert title
            message: Alert description
            severity: Alert severity level
            details: Additional context
            error: Exception object if applicable
            channels: Override default channel selection
        
        Returns:
            Dict with success status for each channel
        """
        results = {}
        
        # Determine channels based on severity if not specified
        if channels is None:
            if severity == AlertSeverity.CRITICAL:
                channels = [NotificationChannel.SLACK, NotificationChannel.EMAIL, NotificationChannel.CLOUDWATCH]
            elif severity == AlertSeverity.ERROR:
                channels = [NotificationChannel.SLACK, NotificationChannel.CLOUDWATCH]
            elif severity == AlertSeverity.WARNING:
                channels = [NotificationChannel.CLOUDWATCH]
            else:
                channels = [NotificationChannel.CLOUDWATCH]
        
        # Send to each channel
        if NotificationChannel.SLACK in channels:
            results["slack"] = await self.slack.send_alert(
                title=title,
                message=message,
                severity=severity,
                details=details,
                error=error,
            )
        
        if NotificationChannel.EMAIL in channels or NotificationChannel.SMS in channels:
            results["sns"] = self.sns.send_alert(
                title=title,
                message=message,
                severity=severity,
                details=details,
            )
        
        if NotificationChannel.CLOUDWATCH in channels:
            # Put error metric to CloudWatch
            results["cloudwatch"] = self.cloudwatch.increment_counter(
                metric_name=f"Alert_{severity.value.capitalize()}",
                dimensions={"AlertType": title.replace(" ", "_")[:50]}
            )
        
        return results
    
    def record_api_error(
        self,
        error_type: str,
        endpoint: str,
        status_code: int,
    ) -> bool:
        """Record an API error metric."""
        return self.cloudwatch.increment_counter(
            metric_name="APIError",
            dimensions={
                "ErrorType": error_type,
                "Endpoint": endpoint[:50],
                "StatusCode": str(status_code),
            }
        )
    
    def record_auth_failure(self, reason: str) -> bool:
        """Record an authentication failure metric."""
        return self.cloudwatch.increment_counter(
            metric_name="AuthenticationFailure",
            dimensions={"Reason": reason}
        )
    
    def record_rate_limit_hit(self, endpoint: str, client_id: str) -> bool:
        """Record a rate limit hit metric."""
        return self.cloudwatch.increment_counter(
            metric_name="RateLimitHit",
            dimensions={
                "Endpoint": endpoint[:50],
                "ClientType": "user" if client_id.startswith("user:") else "ip"
            }
        )
    
    def record_db_health(self, database: str, is_healthy: bool, latency_ms: float) -> bool:
        """Record database health metrics."""
        self.cloudwatch.increment_counter(
            metric_name="DatabaseHealthCheck",
            dimensions={
                "Database": database,
                "Status": "healthy" if is_healthy else "unhealthy"
            }
        )
        
        if is_healthy:
            self.cloudwatch.record_latency(
                metric_name="DatabaseLatency",
                latency_ms=latency_ms,
                dimensions={"Database": database}
            )
        
        return True


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Create a singleton instance for easy access
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


__all__ = [
    "NotificationService",
    "get_notification_service",
    "AlertSeverity",
    "NotificationChannel",
    "SlackNotifier",
    "SNSNotifier",
    "CloudWatchMetrics",
]
