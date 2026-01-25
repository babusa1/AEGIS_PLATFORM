"""Data Quality Engine - SOC 2 Processing Integrity"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import re
import structlog

from aegis_fabric.quality.rules import QualityRule, RuleResult, QualityScore, RuleSeverity, RuleCategory

logger = structlog.get_logger(__name__)


class DataQualityEngine:
    """
    Data quality validation engine.
    
    SOC 2 Processing Integrity: Ensures data accuracy
    HITRUST: Data quality controls
    """
    
    def __init__(self):
        self._rules: list[QualityRule] = []
        self._register_healthcare_rules()
    
    def _register_healthcare_rules(self):
        """Register default healthcare data quality rules."""
        # Patient required fields
        self.add_rule(QualityRule(
            id="pt-required-name",
            name="Patient name required",
            category=RuleCategory.COMPLETENESS,
            severity=RuleSeverity.ERROR,
            check_func=lambda r: bool(r.get("first_name") and r.get("last_name"))
        ))
        
        self.add_rule(QualityRule(
            id="pt-required-dob",
            name="Patient DOB required",
            category=RuleCategory.COMPLETENESS,
            severity=RuleSeverity.ERROR,
            check_func=lambda r: bool(r.get("date_of_birth"))
        ))
        
        # Validity rules
        self.add_rule(QualityRule(
            id="pt-valid-mrn",
            name="Valid MRN format",
            category=RuleCategory.VALIDITY,
            severity=RuleSeverity.WARNING,
            check_func=lambda r: not r.get("mrn") or bool(re.match(r'^[A-Z0-9]{6,}$', str(r.get("mrn", ""))))
        ))
        
        self.add_rule(QualityRule(
            id="pt-valid-gender",
            name="Valid gender value",
            category=RuleCategory.VALIDITY,
            severity=RuleSeverity.WARNING,
            check_func=lambda r: r.get("gender") in [None, "male", "female", "other", "unknown"]
        ))
        
        # Consistency rules
        self.add_rule(QualityRule(
            id="obs-consistency-range",
            name="Observation in valid range",
            category=RuleCategory.CONSISTENCY,
            severity=RuleSeverity.WARNING,
            check_func=self._check_observation_range
        ))
    
    def add_rule(self, rule: QualityRule):
        """Add a quality rule."""
        self._rules.append(rule)
    
    def validate(self, record: dict, record_type: str = "patient") -> QualityScore:
        """Validate a record against quality rules."""
        issues = []
        category_scores = {cat: [] for cat in RuleCategory}
        
        for rule in self._rules:
            try:
                passed = rule.check_func(record)
                if not passed:
                    issues.append(RuleResult(
                        rule_id=rule.id,
                        passed=False,
                        severity=rule.severity,
                        message=rule.name
                    ))
                category_scores[rule.category].append(1.0 if passed else 0.0)
            except Exception as e:
                logger.warning("Rule check failed", rule=rule.id, error=str(e))
        
        # Calculate scores
        def avg(scores): return sum(scores) / len(scores) if scores else 1.0
        
        completeness = avg(category_scores[RuleCategory.COMPLETENESS])
        accuracy = avg(category_scores[RuleCategory.ACCURACY])
        consistency = avg(category_scores[RuleCategory.CONSISTENCY])
        validity = avg(category_scores[RuleCategory.VALIDITY])
        
        overall = (completeness + accuracy + consistency + validity) / 4
        
        return QualityScore(
            overall=overall,
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            validity=validity,
            issues=issues
        )
    
    def validate_batch(self, records: list[dict]) -> dict:
        """Validate a batch of records."""
        total = len(records)
        passed = 0
        all_issues = []
        
        for i, record in enumerate(records):
            score = self.validate(record)
            if score.overall >= 0.8:
                passed += 1
            all_issues.extend(score.issues)
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "issues": all_issues[:100]  # Limit issues
        }
    
    def _check_observation_range(self, record: dict) -> bool:
        """Check if observation value is in valid range."""
        code = record.get("code")
        value = record.get("value")
        
        if not code or value is None:
            return True
        
        # Known ranges
        ranges = {
            "heart_rate": (30, 200),
            "bp_systolic": (60, 250),
            "bp_diastolic": (40, 150),
            "temperature": (35, 42),
            "spo2": (70, 100),
        }
        
        if code in ranges:
            low, high = ranges[code]
            try:
                return low <= float(value) <= high
            except (ValueError, TypeError):
                return False
        
        return True
