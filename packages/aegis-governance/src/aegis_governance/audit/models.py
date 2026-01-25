"""Audit Models"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AuditCategory(str, Enum):
    ACCESS = "access"
    AUTH = "auth"
    DATA_CHANGE = "data_change"
    CONSENT = "consent"
    BTG = "btg"
    ADMIN = "admin"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    id: str
    timestamp: datetime
    category: AuditCategory
    action: str
    actor_id: str
    resource_type: str
    resource_id: str
    tenant_id: str
    outcome: str = "success"
    severity: AuditSeverity = AuditSeverity.INFO
    patient_id: str | None = None
    ip_address: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    hash: str | None = None


@dataclass
class AuditQuery:
    start_time: datetime | None = None
    end_time: datetime | None = None
    category: AuditCategory | None = None
    actor_id: str | None = None
    patient_id: str | None = None
    tenant_id: str | None = None
    limit: int = 100
