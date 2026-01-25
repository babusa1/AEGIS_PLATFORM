"""HITL Approval Workflows"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import structlog

logger = structlog.get_logger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    id: str
    request_type: str
    content: dict
    risk_level: RiskLevel
    requester: str
    tenant_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    ai_confidence: float | None = None


class HITLWorkflow:
    AUTO_THRESHOLD = {RiskLevel.LOW: 0.95, RiskLevel.MEDIUM: 0.99}
    
    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}
    
    def create_request(self, rtype: str, content: dict, risk: RiskLevel,
                      requester: str, tenant: str, confidence: float | None = None) -> ApprovalRequest:
        req = ApprovalRequest(
            id=f"HITL-{uuid.uuid4().hex[:12]}",
            request_type=rtype, content=content, risk_level=risk,
            requester=requester, tenant_id=tenant, ai_confidence=confidence)
        
        threshold = self.AUTO_THRESHOLD.get(risk)
        if threshold and confidence and confidence >= threshold:
            req.status = ApprovalStatus.APPROVED
        else:
            self._requests[req.id] = req
        
        return req
    
    def approve(self, rid: str, reviewer: str):
        if rid in self._requests:
            self._requests[rid].status = ApprovalStatus.APPROVED
    
    def reject(self, rid: str, reviewer: str):
        if rid in self._requests:
            self._requests[rid].status = ApprovalStatus.REJECTED
    
    def get_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]
