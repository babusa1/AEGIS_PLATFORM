"""
AEGIS Human-in-the-Loop Approval Workflow

Manages approval requests for workflow executions requiring human review.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine
from enum import Enum
import asyncio
import uuid
import structlog

logger = structlog.get_logger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ApprovalPriority(str, Enum):
    """Priority levels for approval requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    """A request for human approval."""
    id: str
    execution_id: str
    workflow_id: str
    node_id: str
    title: str
    description: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.MEDIUM
    
    # Request details
    request_data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    
    # Approval outcome
    decision: str | None = None  # approve, reject
    decision_reason: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    escalate_after: datetime | None = None
    
    # Assignment
    assigned_to: list[str] = field(default_factory=list)  # User IDs
    assigned_roles: list[str] = field(default_factory=list)  # Role names
    
    # Tracking
    tenant_id: str = "default"
    notification_sent: bool = False
    reminder_count: int = 0


@dataclass
class ApprovalPolicy:
    """Policy for automatic approval handling."""
    id: str
    name: str
    workflow_id: str | None = None  # None = applies to all
    node_id: str | None = None
    
    # Auto-approval conditions
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)
    
    # Timeout handling
    timeout_minutes: int = 1440  # 24 hours
    timeout_action: str = "escalate"  # escalate, auto_approve, auto_reject
    
    # Escalation
    escalate_after_minutes: int = 720  # 12 hours
    escalate_to: list[str] = field(default_factory=list)  # User IDs or roles


class ApprovalManager:
    """
    Manages human-in-the-loop approval workflows.
    
    Features:
    - Create approval requests
    - Approve/reject with audit trail
    - Automatic timeout and escalation
    - Notification integration
    - Policy-based auto-approval
    """
    
    def __init__(
        self,
        notification_callback: Callable[[ApprovalRequest], Coroutine[Any, Any, None]] | None = None,
        default_timeout_minutes: int = 1440,
    ):
        """
        Initialize the approval manager.
        
        Args:
            notification_callback: Async function to send notifications
            default_timeout_minutes: Default expiration time
        """
        self.notification_callback = notification_callback
        self.default_timeout_minutes = default_timeout_minutes
        
        self._requests: dict[str, ApprovalRequest] = {}
        self._policies: dict[str, ApprovalPolicy] = {}
        self._running = False
        self._timeout_task: asyncio.Task | None = None
        
        # Callbacks for workflow continuation
        self._on_approved: dict[str, Callable] = {}
        self._on_rejected: dict[str, Callable] = {}
    
    async def start(self):
        """Start the approval manager background tasks."""
        if self._running:
            return
        
        self._running = True
        self._timeout_task = asyncio.create_task(self._timeout_loop())
        logger.info("Approval manager started")
    
    async def stop(self):
        """Stop the approval manager."""
        self._running = False
        
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Approval manager stopped")
    
    async def _timeout_loop(self):
        """Background loop to handle timeouts and escalations."""
        while self._running:
            try:
                await self._process_timeouts()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Timeout loop error", error=str(e))
                await asyncio.sleep(60)
    
    async def _process_timeouts(self):
        """Process expired and escalation-due requests."""
        now = datetime.now(timezone.utc)
        
        for request in self._requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue
            
            # Check expiration
            if request.expires_at and request.expires_at <= now:
                await self._handle_timeout(request)
                continue
            
            # Check escalation
            if request.escalate_after and request.escalate_after <= now:
                if request.status == ApprovalStatus.PENDING:
                    await self._handle_escalation(request)
    
    async def _handle_timeout(self, request: ApprovalRequest):
        """Handle an expired approval request."""
        policy = self._get_policy_for_request(request)
        
        if policy and policy.timeout_action == "auto_approve":
            await self.approve(
                request.id,
                approver="system",
                comment="Auto-approved due to timeout",
            )
        elif policy and policy.timeout_action == "auto_reject":
            await self.reject(
                request.id,
                rejector="system",
                reason="Auto-rejected due to timeout",
            )
        else:
            request.status = ApprovalStatus.EXPIRED
            logger.warning(
                "Approval request expired",
                request_id=request.id,
                execution_id=request.execution_id,
            )
    
    async def _handle_escalation(self, request: ApprovalRequest):
        """Handle escalation of a pending request."""
        request.status = ApprovalStatus.ESCALATED
        
        policy = self._get_policy_for_request(request)
        if policy and policy.escalate_to:
            request.assigned_to.extend(policy.escalate_to)
        
        logger.info(
            "Approval request escalated",
            request_id=request.id,
            escalated_to=request.assigned_to,
        )
        
        # Send escalation notification
        if self.notification_callback:
            try:
                await self.notification_callback(request)
            except Exception as e:
                logger.error("Escalation notification failed", error=str(e))
    
    def _get_policy_for_request(self, request: ApprovalRequest) -> ApprovalPolicy | None:
        """Get the applicable policy for a request."""
        for policy in self._policies.values():
            if policy.workflow_id and policy.workflow_id != request.workflow_id:
                continue
            if policy.node_id and policy.node_id != request.node_id:
                continue
            return policy
        return None
    
    async def request_approval(
        self,
        execution_id: str,
        workflow_id: str,
        node_id: str,
        title: str,
        description: str,
        request_data: dict | None = None,
        context: dict | None = None,
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        assigned_to: list[str] | None = None,
        assigned_roles: list[str] | None = None,
        timeout_minutes: int | None = None,
        tenant_id: str = "default",
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            execution_id: ID of the workflow execution
            workflow_id: ID of the workflow
            node_id: ID of the node requiring approval
            title: Short title for the request
            description: Detailed description
            request_data: Data being approved
            context: Additional context
            priority: Request priority
            assigned_to: User IDs who can approve
            assigned_roles: Roles who can approve
            timeout_minutes: Custom timeout
            tenant_id: Tenant ID
        
        Returns:
            ApprovalRequest
        """
        request_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        timeout = timeout_minutes or self.default_timeout_minutes
        
        request = ApprovalRequest(
            id=request_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            node_id=node_id,
            title=title,
            description=description,
            priority=priority,
            request_data=request_data or {},
            context=context or {},
            assigned_to=assigned_to or [],
            assigned_roles=assigned_roles or ["approver"],
            expires_at=now + timedelta(minutes=timeout),
            escalate_after=now + timedelta(minutes=timeout // 2),
            tenant_id=tenant_id,
        )
        
        self._requests[request_id] = request
        
        logger.info(
            "Approval request created",
            request_id=request_id,
            execution_id=execution_id,
            title=title,
        )
        
        # Send notification
        if self.notification_callback:
            try:
                await self.notification_callback(request)
                request.notification_sent = True
            except Exception as e:
                logger.error("Notification failed", error=str(e))
        
        return request
    
    async def approve(
        self,
        request_id: str,
        approver: str,
        comment: str | None = None,
    ) -> ApprovalRequest:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request
            approver: User ID of the approver
            comment: Optional comment
        
        Returns:
            Updated ApprovalRequest
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")
        
        if request.status not in [ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]:
            raise ValueError(f"Request is not pending: {request.status}")
        
        request.status = ApprovalStatus.APPROVED
        request.decision = "approve"
        request.decision_reason = comment
        request.decided_by = approver
        request.decided_at = datetime.now(timezone.utc)
        
        logger.info(
            "Approval request approved",
            request_id=request_id,
            approver=approver,
        )
        
        # Trigger callback
        if request_id in self._on_approved:
            try:
                await self._on_approved[request_id](request)
            except Exception as e:
                logger.error("Approval callback failed", error=str(e))
        
        return request
    
    async def reject(
        self,
        request_id: str,
        rejector: str,
        reason: str,
    ) -> ApprovalRequest:
        """
        Reject a pending request.
        
        Args:
            request_id: ID of the request
            rejector: User ID of the rejector
            reason: Reason for rejection
        
        Returns:
            Updated ApprovalRequest
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")
        
        if request.status not in [ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]:
            raise ValueError(f"Request is not pending: {request.status}")
        
        request.status = ApprovalStatus.REJECTED
        request.decision = "reject"
        request.decision_reason = reason
        request.decided_by = rejector
        request.decided_at = datetime.now(timezone.utc)
        
        logger.info(
            "Approval request rejected",
            request_id=request_id,
            rejector=rejector,
            reason=reason,
        )
        
        # Trigger callback
        if request_id in self._on_rejected:
            try:
                await self._on_rejected[request_id](request)
            except Exception as e:
                logger.error("Rejection callback failed", error=str(e))
        
        return request
    
    def on_approved(
        self,
        request_id: str,
        callback: Callable[[ApprovalRequest], Coroutine[Any, Any, None]],
    ):
        """Register a callback for when a request is approved."""
        self._on_approved[request_id] = callback
    
    def on_rejected(
        self,
        request_id: str,
        callback: Callable[[ApprovalRequest], Coroutine[Any, Any, None]],
    ):
        """Register a callback for when a request is rejected."""
        self._on_rejected[request_id] = callback
    
    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get a specific approval request."""
        return self._requests.get(request_id)
    
    def list_pending(
        self,
        user_id: str | None = None,
        roles: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[ApprovalRequest]:
        """
        List pending approval requests.
        
        Args:
            user_id: Filter by assigned user
            roles: Filter by assigned roles
            tenant_id: Filter by tenant
        
        Returns:
            List of pending ApprovalRequests
        """
        requests = [
            r for r in self._requests.values()
            if r.status in [ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]
        ]
        
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]
        
        if user_id:
            requests = [r for r in requests if user_id in r.assigned_to]
        
        if roles:
            requests = [
                r for r in requests
                if any(role in r.assigned_roles for role in roles)
            ]
        
        # Sort by priority and creation time
        priority_order = {
            ApprovalPriority.CRITICAL: 0,
            ApprovalPriority.HIGH: 1,
            ApprovalPriority.MEDIUM: 2,
            ApprovalPriority.LOW: 3,
        }
        requests.sort(key=lambda r: (priority_order.get(r.priority, 2), r.created_at))
        
        return requests
    
    def list_all(
        self,
        tenant_id: str | None = None,
        status: ApprovalStatus | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List all approval requests."""
        requests = list(self._requests.values())
        
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        # Sort by creation time (newest first)
        requests.sort(key=lambda r: r.created_at, reverse=True)
        
        return requests[:limit]
    
    def add_policy(self, policy: ApprovalPolicy):
        """Add an approval policy."""
        self._policies[policy.id] = policy
        logger.info("Approval policy added", policy_id=policy.id, name=policy.name)
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove an approval policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False


# =============================================================================
# Global Manager Instance
# =============================================================================

_approval_manager: ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    """Get the global approval manager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


async def init_approval_manager(
    notification_callback: Callable[[ApprovalRequest], Coroutine[Any, Any, None]] | None = None,
) -> ApprovalManager:
    """Initialize and start the global approval manager."""
    global _approval_manager
    _approval_manager = ApprovalManager(notification_callback=notification_callback)
    await _approval_manager.start()
    return _approval_manager
