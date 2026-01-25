"""Data Retention Manager - SOC 2 Confidentiality"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class RetentionAction(str, Enum):
    RETAIN = "retain"
    ARCHIVE = "archive"
    DELETE = "delete"
    LEGAL_HOLD = "legal_hold"


@dataclass
class RetentionPolicy:
    id: str
    name: str
    data_type: str
    retention_days: int
    action: RetentionAction
    archive_after_days: int | None = None
    legal_hold_override: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetentionRecord:
    record_id: str
    data_type: str
    created_at: datetime
    policy_id: str
    legal_hold: bool = False
    legal_hold_reason: str | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None


class RetentionManager:
    """
    Data retention policy management.
    
    SOC 2 Confidentiality: Data retention and disposal
    HITRUST 09.c: Disposal of media
    """
    
    # Default retention periods (in days)
    HEALTHCARE_DEFAULTS = {
        "patient_record": 365 * 7,  # 7 years
        "audit_log": 365 * 7,
        "billing": 365 * 7,
        "consent": 365 * 10,
        "employee": 365 * 7,
        "temp": 90,
    }
    
    def __init__(self, delete_callback: Callable | None = None,
                archive_callback: Callable | None = None):
        self._policies: dict[str, RetentionPolicy] = {}
        self._records: dict[str, RetentionRecord] = {}
        self._legal_holds: set[str] = set()
        self._delete = delete_callback
        self._archive = archive_callback
        
        self._register_default_policies()
    
    def _register_default_policies(self):
        """Register default healthcare retention policies."""
        for dtype, days in self.HEALTHCARE_DEFAULTS.items():
            self.register_policy(RetentionPolicy(
                id=f"default-{dtype}",
                name=f"Default {dtype} retention",
                data_type=dtype,
                retention_days=days,
                action=RetentionAction.DELETE,
                archive_after_days=days - 365 if days > 365 else None
            ))
    
    def register_policy(self, policy: RetentionPolicy):
        """Register a retention policy."""
        self._policies[policy.id] = policy
        logger.info("Retention policy registered", policy_id=policy.id, days=policy.retention_days)
    
    def track_record(self, record_id: str, data_type: str, created_at: datetime | None = None):
        """Start tracking a record for retention."""
        policy = self._get_policy_for_type(data_type)
        
        self._records[record_id] = RetentionRecord(
            record_id=record_id,
            data_type=data_type,
            created_at=created_at or datetime.utcnow(),
            policy_id=policy.id if policy else "default"
        )
    
    def apply_legal_hold(self, record_id: str, reason: str):
        """Apply legal hold to prevent deletion."""
        if record_id in self._records:
            self._records[record_id].legal_hold = True
            self._records[record_id].legal_hold_reason = reason
            self._legal_holds.add(record_id)
            logger.warning("Legal hold applied", record_id=record_id, reason=reason)
    
    def release_legal_hold(self, record_id: str):
        """Release legal hold."""
        if record_id in self._records:
            self._records[record_id].legal_hold = False
            self._records[record_id].legal_hold_reason = None
            self._legal_holds.discard(record_id)
    
    def process_retention(self) -> dict[str, list[str]]:
        """Process retention policies and return actions taken."""
        now = datetime.utcnow()
        results = {"archived": [], "deleted": [], "retained": [], "held": []}
        
        for record_id, record in self._records.items():
            if record.deleted_at:
                continue
            
            policy = self._policies.get(record.policy_id)
            if not policy:
                continue
            
            age_days = (now - record.created_at).days
            
            # Check legal hold
            if record.legal_hold:
                results["held"].append(record_id)
                continue
            
            # Check for archival
            if policy.archive_after_days and age_days >= policy.archive_after_days and not record.archived_at:
                record.archived_at = now
                if self._archive:
                    self._archive(record_id)
                results["archived"].append(record_id)
                continue
            
            # Check for deletion
            if age_days >= policy.retention_days:
                record.deleted_at = now
                if self._delete:
                    self._delete(record_id)
                results["deleted"].append(record_id)
            else:
                results["retained"].append(record_id)
        
        logger.info("Retention processed",
            archived=len(results["archived"]),
            deleted=len(results["deleted"]),
            held=len(results["held"]))
        
        return results
    
    def get_expiring_soon(self, days: int = 30) -> list[RetentionRecord]:
        """Get records expiring within specified days."""
        now = datetime.utcnow()
        expiring = []
        
        for record in self._records.values():
            if record.deleted_at or record.legal_hold:
                continue
            
            policy = self._policies.get(record.policy_id)
            if not policy:
                continue
            
            expires_at = record.created_at + timedelta(days=policy.retention_days)
            if (expires_at - now).days <= days:
                expiring.append(record)
        
        return expiring
    
    def _get_policy_for_type(self, data_type: str) -> RetentionPolicy | None:
        for policy in self._policies.values():
            if policy.data_type == data_type:
                return policy
        return None
