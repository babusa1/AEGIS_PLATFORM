"""
Human-in-the-Loop (HITL)

Approval workflows for sensitive AI actions.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable
from uuid import uuid4
import structlog

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str
    action_details: dict = Field(default_factory=dict)
    agent_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    patient_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_id: str | None = None
    notes: str | None = None
    risk_level: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    resolved_at: datetime | None = None


class ApprovalWorkflow:
    """Manages approval workflows for agent actions."""
    
    def __init__(self, timeout_minutes: int = 30):
        self.timeout = timedelta(minutes=timeout_minutes)
        self._pending: dict[str, ApprovalRequest] = {}
        self._handlers: list[Callable] = []
    
    def add_handler(self, handler: Callable) -> None:
        self._handlers.append(handler)
    
    async def request_approval(
        self,
        action_type: str,
        action_details: dict,
        context: dict | None = None,
        risk_level: str = "medium",
    ) -> ApprovalRequest:
        context = context or {}
        
        request = ApprovalRequest(
            action_type=action_type,
            action_details=action_details,
            agent_id=context.get("agent_id"),
            tenant_id=context.get("tenant_id"),
            user_id=context.get("user_id"),
            patient_id=context.get("patient_id"),
            risk_level=risk_level,
            expires_at=datetime.utcnow() + self.timeout,
        )
        
        self._pending[request.id] = request
        
        for handler in self._handlers:
            try:
                await handler(request)
            except Exception as e:
                logger.error("Handler failed", error=str(e))
        
        return request
    
    async def resolve(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        notes: str | None = None,
    ) -> ApprovalRequest | None:
        request = self._pending.get(request_id)
        if not request:
            return None
        
        if request.expires_at and datetime.utcnow() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            del self._pending[request_id]
            return request
        
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.approver_id = approver_id
        request.notes = notes
        request.resolved_at = datetime.utcnow()
        
        del self._pending[request_id]
        return request
    
    def get_pending(self, tenant_id: str | None = None) -> list[ApprovalRequest]:
        requests = list(self._pending.values())
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]
        return requests


_workflow: ApprovalWorkflow | None = None


def get_approval_workflow() -> ApprovalWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = ApprovalWorkflow()
    return _workflow
