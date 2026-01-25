"""Guardrails Engine - AI Safety Framework"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import re
import structlog

logger = structlog.get_logger(__name__)


class GuardrailType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    CONTENT = "content"
    PII = "pii"
    HALLUCINATION = "hallucination"
    MEDICAL = "medical"


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"
    REDACT = "redact"
    ESCALATE = "escalate"


@dataclass
class GuardrailResult:
    passed: bool
    guardrail_type: GuardrailType
    action: GuardrailAction
    reason: str
    violations: list[str] = field(default_factory=list)
    modified_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailCheck:
    name: str
    guardrail_type: GuardrailType
    check_func: Callable[[str, dict], GuardrailResult]
    enabled: bool = True
    priority: int = 100


class GuardrailsEngine:
    """
    AI Guardrails Framework for healthcare.
    
    SOC 2 Processing Integrity: Ensures AI outputs are valid
    HITRUST: Safety controls for AI-generated content
    """
    
    def __init__(self):
        self._checks: list[GuardrailCheck] = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default healthcare guardrails."""
        # PII Detection
        self.register_check(GuardrailCheck(
            name="pii_detection",
            guardrail_type=GuardrailType.PII,
            check_func=self._check_pii,
            priority=10
        ))
        
        # Medical advice disclaimer
        self.register_check(GuardrailCheck(
            name="medical_disclaimer",
            guardrail_type=GuardrailType.MEDICAL,
            check_func=self._check_medical_advice,
            priority=20
        ))
        
        # Prohibited content
        self.register_check(GuardrailCheck(
            name="prohibited_content",
            guardrail_type=GuardrailType.CONTENT,
            check_func=self._check_prohibited,
            priority=5
        ))
    
    def register_check(self, check: GuardrailCheck):
        """Register a guardrail check."""
        self._checks.append(check)
        self._checks.sort(key=lambda c: c.priority)
    
    def check_input(self, content: str, context: dict | None = None) -> list[GuardrailResult]:
        """Run input guardrails on user input."""
        context = context or {}
        context["direction"] = "input"
        return self._run_checks(content, context, [GuardrailType.INPUT, GuardrailType.PII, GuardrailType.CONTENT])
    
    def check_output(self, content: str, context: dict | None = None) -> list[GuardrailResult]:
        """Run output guardrails on AI response."""
        context = context or {}
        context["direction"] = "output"
        return self._run_checks(content, context, [GuardrailType.OUTPUT, GuardrailType.PII, 
                                                   GuardrailType.MEDICAL, GuardrailType.HALLUCINATION])
    
    def _run_checks(self, content: str, context: dict, types: list[GuardrailType]) -> list[GuardrailResult]:
        """Run applicable guardrail checks."""
        results = []
        for check in self._checks:
            if not check.enabled or check.guardrail_type not in types:
                continue
            try:
                result = check.check_func(content, context)
                results.append(result)
                if result.action == GuardrailAction.BLOCK:
                    logger.warning("Guardrail blocked", check=check.name, reason=result.reason)
                    break
            except Exception as e:
                logger.error("Guardrail check failed", check=check.name, error=str(e))
        return results
    
    def should_block(self, results: list[GuardrailResult]) -> bool:
        """Check if any guardrail requires blocking."""
        return any(r.action == GuardrailAction.BLOCK for r in results)
    
    def get_violations(self, results: list[GuardrailResult]) -> list[str]:
        """Get all violations from results."""
        violations = []
        for r in results:
            violations.extend(r.violations)
        return violations
    
    def _check_pii(self, content: str, context: dict) -> GuardrailResult:
        """Check for PII in content."""
        violations = []
        
        # SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', content):
            violations.append("SSN detected")
        
        # Phone number
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content):
            violations.append("Phone number detected")
        
        # Email
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
            violations.append("Email detected")
        
        # MRN pattern
        if re.search(r'\bMRN[:\s]*\d{6,}\b', content, re.IGNORECASE):
            violations.append("MRN detected")
        
        if violations:
            return GuardrailResult(
                passed=False,
                guardrail_type=GuardrailType.PII,
                action=GuardrailAction.REDACT if context.get("direction") == "output" else GuardrailAction.WARN,
                reason="PII detected in content",
                violations=violations
            )
        
        return GuardrailResult(
            passed=True, guardrail_type=GuardrailType.PII,
            action=GuardrailAction.ALLOW, reason="No PII detected")
    
    def _check_medical_advice(self, content: str, context: dict) -> GuardrailResult:
        """Check for medical advice requiring disclaimer."""
        medical_keywords = ["diagnosis", "prescribe", "treatment", "medication", 
                          "dosage", "take this", "you should", "recommend"]
        
        content_lower = content.lower()
        found = [kw for kw in medical_keywords if kw in content_lower]
        
        if found and context.get("direction") == "output":
            return GuardrailResult(
                passed=True,
                guardrail_type=GuardrailType.MEDICAL,
                action=GuardrailAction.WARN,
                reason="Medical content detected - disclaimer may be needed",
                violations=found,
                metadata={"needs_disclaimer": True}
            )
        
        return GuardrailResult(
            passed=True, guardrail_type=GuardrailType.MEDICAL,
            action=GuardrailAction.ALLOW, reason="No medical advice detected")
    
    def _check_prohibited(self, content: str, context: dict) -> GuardrailResult:
        """Check for prohibited content."""
        prohibited = ["harm", "suicide", "self-harm", "abuse"]
        content_lower = content.lower()
        
        found = [p for p in prohibited if p in content_lower]
        if found:
            return GuardrailResult(
                passed=False,
                guardrail_type=GuardrailType.CONTENT,
                action=GuardrailAction.ESCALATE,
                reason="Prohibited content detected",
                violations=found,
                metadata={"escalate_to": "clinical_team"}
            )
        
        return GuardrailResult(
            passed=True, guardrail_type=GuardrailType.CONTENT,
            action=GuardrailAction.ALLOW, reason="No prohibited content")
