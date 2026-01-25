"""Data Quality Rules"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RuleSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(str, Enum):
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"


@dataclass
class QualityRule:
    id: str
    name: str
    category: RuleCategory
    severity: RuleSeverity
    check_func: Callable[[dict], bool]
    description: str = ""
    threshold: float = 1.0


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    severity: RuleSeverity
    message: str
    field: str | None = None
    value: Any = None


@dataclass
class QualityScore:
    overall: float
    completeness: float
    accuracy: float
    consistency: float
    validity: float
    issues: list[RuleResult] = field(default_factory=list)
