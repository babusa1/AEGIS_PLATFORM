"""Policy Engine - HITRUST 05.a, OPA-style policies"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PolicyCondition:
    """A condition in a policy rule."""
    field: str
    operator: str  # eq, neq, in, contains, gt, lt, regex
    value: Any


@dataclass
class PolicyRule:
    """A rule within a policy."""
    effect: PolicyEffect
    actions: list[str]
    resources: list[str]
    conditions: list[PolicyCondition] = field(default_factory=list)


@dataclass
class Policy:
    """Access control policy."""
    id: str
    name: str
    description: str
    rules: list[PolicyRule]
    priority: int = 100  # Lower = higher priority
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    allowed: bool
    policy_id: str | None
    rule_index: int | None
    reason: str
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


class PolicyEngine:
    """
    Centralized policy engine (OPA-style).
    
    HITRUST 05.a: Information security policy
    SOC 2 Security: Access control policies
    """
    
    def __init__(self, default_effect: PolicyEffect = PolicyEffect.DENY):
        self._policies: dict[str, Policy] = {}
        self._default_effect = default_effect
        self._custom_evaluators: dict[str, Callable] = {}
    
    def register_policy(self, policy: Policy):
        """Register a new policy."""
        self._policies[policy.id] = policy
        logger.info("Policy registered", policy_id=policy.id, name=policy.name)
    
    def evaluate(self, action: str, resource: str, 
                context: dict[str, Any]) -> PolicyDecision:
        """
        Evaluate policies for an action on a resource.
        
        Returns PolicyDecision with allow/deny and reason.
        """
        # Sort policies by priority
        sorted_policies = sorted(
            [p for p in self._policies.values() if p.enabled],
            key=lambda p: p.priority
        )
        
        for policy in sorted_policies:
            for i, rule in enumerate(policy.rules):
                if self._rule_matches(rule, action, resource, context):
                    decision = PolicyDecision(
                        allowed=rule.effect == PolicyEffect.ALLOW,
                        policy_id=policy.id,
                        rule_index=i,
                        reason=f"Matched policy '{policy.name}' rule {i}"
                    )
                    logger.debug("Policy evaluated",
                        action=action,
                        resource=resource,
                        decision=decision.allowed,
                        policy=policy.id)
                    return decision
        
        # No matching policy - use default
        return PolicyDecision(
            allowed=self._default_effect == PolicyEffect.ALLOW,
            policy_id=None,
            rule_index=None,
            reason=f"No matching policy, default: {self._default_effect.value}"
        )
    
    def _rule_matches(self, rule: PolicyRule, action: str, 
                     resource: str, context: dict) -> bool:
        """Check if a rule matches the request."""
        # Check action match
        if not self._matches_pattern(action, rule.actions):
            return False
        
        # Check resource match
        if not self._matches_pattern(resource, rule.resources):
            return False
        
        # Check conditions
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        
        return True
    
    def _matches_pattern(self, value: str, patterns: list[str]) -> bool:
        """Check if value matches any pattern (supports * wildcard)."""
        for pattern in patterns:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                if value.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith("*"):
                if value.endswith(pattern[1:]):
                    return True
            elif pattern == value:
                return True
        return False
    
    def _evaluate_condition(self, condition: PolicyCondition, 
                           context: dict) -> bool:
        """Evaluate a single condition."""
        # Get field value from context
        value = context.get(condition.field)
        
        op = condition.operator
        expected = condition.value
        
        if op == "eq":
            return value == expected
        elif op == "neq":
            return value != expected
        elif op == "in":
            return value in expected
        elif op == "contains":
            return expected in value if value else False
        elif op == "gt":
            return value > expected if value else False
        elif op == "lt":
            return value < expected if value else False
        elif op == "exists":
            return value is not None
        elif op == "not_exists":
            return value is None
        
        return False
    
    def register_evaluator(self, name: str, func: Callable):
        """Register a custom condition evaluator."""
        self._custom_evaluators[name] = func
    
    def get_policy(self, policy_id: str) -> Policy | None:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> list[Policy]:
        """List all registered policies."""
        return list(self._policies.values())
    
    def disable_policy(self, policy_id: str):
        """Disable a policy."""
        if policy_id in self._policies:
            self._policies[policy_id].enabled = False
    
    def enable_policy(self, policy_id: str):
        """Enable a policy."""
        if policy_id in self._policies:
            self._policies[policy_id].enabled = True


# Pre-built healthcare policies
def create_hipaa_minimum_necessary_policy() -> Policy:
    """HIPAA Minimum Necessary policy."""
    return Policy(
        id="hipaa-minimum-necessary",
        name="HIPAA Minimum Necessary",
        description="Limit PHI access to minimum necessary for job function",
        priority=10,
        rules=[
            PolicyRule(
                effect=PolicyEffect.DENY,
                actions=["read:phi:*"],
                resources=["patient:*"],
                conditions=[
                    PolicyCondition("user.role", "neq", "provider"),
                    PolicyCondition("user.role", "neq", "nurse"),
                    PolicyCondition("purpose", "neq", "treatment")
                ]
            )
        ]
    )


def create_sensitive_data_policy() -> Policy:
    """Sensitive data categories policy."""
    return Policy(
        id="sensitive-data-access",
        name="Sensitive Data Access Control",
        description="Extra controls for sensitive data categories",
        priority=5,
        rules=[
            PolicyRule(
                effect=PolicyEffect.DENY,
                actions=["read", "export"],
                resources=["data:mental_health:*", "data:substance:*", "data:hiv:*"],
                conditions=[
                    PolicyCondition("user.clearance", "neq", "sensitive")
                ]
            )
        ]
    )
