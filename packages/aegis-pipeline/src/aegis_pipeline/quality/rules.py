"""
Data Quality Rules
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
import re


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(str, Enum):
    COMPLETENESS = "completeness"
    CONFORMANCE = "conformance"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"


@dataclass
class ValidationResult:
    rule_id: str
    passed: bool
    severity: Severity
    category: RuleCategory
    message: str
    field: str | None = None
    expected: Any = None
    actual: Any = None


@dataclass
class QualityRule:
    id: str
    name: str
    description: str
    category: RuleCategory
    severity: Severity
    check: Callable[[dict], ValidationResult]
    enabled: bool = True
    
    def validate(self, data: dict) -> ValidationResult:
        if not self.enabled:
            return ValidationResult(
                rule_id=self.id,
                passed=True,
                severity=self.severity,
                category=self.category,
                message="Rule disabled",
            )
        return self.check(data)


def required_field(field_name: str, severity: Severity = Severity.ERROR) -> QualityRule:
    def check(data: dict) -> ValidationResult:
        value = data.get(field_name)
        passed = value is not None and value != ""
        return ValidationResult(
            rule_id=f"required_{field_name}",
            passed=passed,
            severity=severity,
            category=RuleCategory.COMPLETENESS,
            message=f"Required field '{field_name}' is missing" if not passed else "OK",
            field=field_name,
            actual=value,
        )
    
    return QualityRule(
        id=f"required_{field_name}",
        name=f"Required: {field_name}",
        description=f"Validates that {field_name} is present",
        category=RuleCategory.COMPLETENESS,
        severity=severity,
        check=check,
    )


def valid_date(field_name: str, severity: Severity = Severity.ERROR) -> QualityRule:
    def check(data: dict) -> ValidationResult:
        value = data.get(field_name)
        if not value:
            return ValidationResult(
                rule_id=f"valid_date_{field_name}",
                passed=True,
                severity=severity,
                category=RuleCategory.CONFORMANCE,
                message="Field not present",
                field=field_name,
            )
        
        patterns = [r"^\d{4}-\d{2}-\d{2}$", r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"]
        passed = any(re.match(p, str(value)) for p in patterns)
        
        return ValidationResult(
            rule_id=f"valid_date_{field_name}",
            passed=passed,
            severity=severity,
            category=RuleCategory.CONFORMANCE,
            message=f"Invalid date format" if not passed else "OK",
            field=field_name,
            actual=value,
        )
    
    return QualityRule(
        id=f"valid_date_{field_name}",
        name=f"Valid Date: {field_name}",
        description=f"Validates ISO date format",
        category=RuleCategory.CONFORMANCE,
        severity=severity,
        check=check,
    )


def valid_code(field_name: str, allowed: list[str], severity: Severity = Severity.ERROR) -> QualityRule:
    def check(data: dict) -> ValidationResult:
        value = data.get(field_name)
        if not value:
            return ValidationResult(
                rule_id=f"valid_code_{field_name}",
                passed=True,
                severity=severity,
                category=RuleCategory.CONFORMANCE,
                message="Field not present",
                field=field_name,
            )
        
        passed = value in allowed
        return ValidationResult(
            rule_id=f"valid_code_{field_name}",
            passed=passed,
            severity=severity,
            category=RuleCategory.CONFORMANCE,
            message=f"Invalid code" if not passed else "OK",
            field=field_name,
            expected=allowed,
            actual=value,
        )
    
    return QualityRule(
        id=f"valid_code_{field_name}",
        name=f"Valid Code: {field_name}",
        description=f"Validates against allowed values",
        category=RuleCategory.CONFORMANCE,
        severity=severity,
        check=check,
    )


def valid_range(field_name: str, min_val: float = None, max_val: float = None) -> QualityRule:
    def check(data: dict) -> ValidationResult:
        value = data.get(field_name)
        if value is None:
            return ValidationResult(
                rule_id=f"valid_range_{field_name}",
                passed=True,
                severity=Severity.WARNING,
                category=RuleCategory.ACCURACY,
                message="Field not present",
                field=field_name,
            )
        
        try:
            num = float(value)
        except (ValueError, TypeError):
            return ValidationResult(
                rule_id=f"valid_range_{field_name}",
                passed=False,
                severity=Severity.WARNING,
                category=RuleCategory.ACCURACY,
                message="Not numeric",
                field=field_name,
                actual=value,
            )
        
        passed = True
        if min_val is not None and num < min_val:
            passed = False
        if max_val is not None and num > max_val:
            passed = False
        
        return ValidationResult(
            rule_id=f"valid_range_{field_name}",
            passed=passed,
            severity=Severity.WARNING,
            category=RuleCategory.ACCURACY,
            message="Out of range" if not passed else "OK",
            field=field_name,
            actual=num,
        )
    
    return QualityRule(
        id=f"valid_range_{field_name}",
        name=f"Valid Range: {field_name}",
        description=f"Validates numeric range",
        category=RuleCategory.ACCURACY,
        severity=Severity.WARNING,
        check=check,
    )


# Healthcare-specific rule sets
PATIENT_RULES = [
    required_field("id"),
    required_field("tenant_id"),
    valid_date("birth_date"),
    valid_code("gender", ["male", "female", "other", "unknown"]),
]

ENCOUNTER_RULES = [
    required_field("id"),
    required_field("tenant_id"),
    valid_date("start_date"),
    valid_code("status", ["planned", "arrived", "in-progress", "finished", "cancelled"]),
]

OBSERVATION_RULES = [
    required_field("id"),
    required_field("code"),
    valid_date("effective_date"),
]

CLAIM_RULES = [
    required_field("id"),
    required_field("tenant_id"),
    valid_date("service_date"),
    valid_range("billed_amount", min_val=0),
]
