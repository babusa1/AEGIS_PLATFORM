"""
Data Quality Validator

Validates healthcare data against configurable rules.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import structlog

from aegis_pipeline.quality.rules import (
    QualityRule,
    ValidationResult,
    Severity,
    RuleCategory,
    PATIENT_RULES,
    ENCOUNTER_RULES,
    OBSERVATION_RULES,
    CLAIM_RULES,
)

logger = structlog.get_logger(__name__)


@dataclass
class ValidationReport:
    """Complete validation report for a record."""
    valid: bool
    errors: list[ValidationResult] = field(default_factory=list)
    warnings: list[ValidationResult] = field(default_factory=list)
    info: list[ValidationResult] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [
                {"rule": e.rule_id, "field": e.field, "message": e.message}
                for e in self.errors
            ],
            "warnings": [
                {"rule": w.rule_id, "field": w.field, "message": w.message}
                for w in self.warnings
            ],
            "validated_at": self.validated_at,
        }


class DataQualityValidator:
    """
    Validates healthcare data against quality rules.
    
    Usage:
        validator = DataQualityValidator()
        
        # Validate a patient record
        report = validator.validate(patient_data, "Patient")
        
        if not report.valid:
            print(f"Validation failed: {report.error_count} errors")
    """
    
    # Default rules by vertex label
    DEFAULT_RULES: dict[str, list[QualityRule]] = {
        "Patient": PATIENT_RULES,
        "Encounter": ENCOUNTER_RULES,
        "Observation": OBSERVATION_RULES,
        "Claim": CLAIM_RULES,
    }
    
    def __init__(self, custom_rules: dict[str, list[QualityRule]] | None = None):
        """
        Initialize validator.
        
        Args:
            custom_rules: Optional custom rules by label
        """
        self.rules = {**self.DEFAULT_RULES}
        
        if custom_rules:
            for label, rules in custom_rules.items():
                if label in self.rules:
                    self.rules[label].extend(rules)
                else:
                    self.rules[label] = rules
    
    def validate(
        self,
        data: dict,
        label: str | None = None,
        rules: list[QualityRule] | None = None,
    ) -> ValidationReport:
        """
        Validate a data record.
        
        Args:
            data: Record to validate
            label: Vertex label (to select rules)
            rules: Override rules to use
            
        Returns:
            ValidationReport with results
        """
        # Determine rules to use
        if rules:
            active_rules = rules
        elif label and label in self.rules:
            active_rules = self.rules[label]
        else:
            active_rules = []
        
        errors = []
        warnings = []
        info = []
        
        # Run each rule
        for rule in active_rules:
            result = rule.validate(data)
            
            if not result.passed:
                if result.severity == Severity.ERROR:
                    errors.append(result)
                elif result.severity == Severity.WARNING:
                    warnings.append(result)
                else:
                    info.append(result)
        
        report = ValidationReport(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
        )
        
        logger.debug(
            "Validation complete",
            label=label,
            valid=report.valid,
            errors=report.error_count,
            warnings=report.warning_count,
        )
        
        return report
    
    def validate_batch(
        self,
        records: list[dict],
        label: str | None = None,
    ) -> tuple[list[dict], list[dict], list[ValidationReport]]:
        """
        Validate multiple records.
        
        Args:
            records: List of records to validate
            label: Vertex label for rules
            
        Returns:
            Tuple of (valid_records, invalid_records, reports)
        """
        valid = []
        invalid = []
        reports = []
        
        for record in records:
            report = self.validate(record, label)
            reports.append(report)
            
            if report.valid:
                valid.append(record)
            else:
                invalid.append(record)
        
        logger.info(
            "Batch validation complete",
            total=len(records),
            valid=len(valid),
            invalid=len(invalid),
        )
        
        return valid, invalid, reports
    
    def add_rule(self, label: str, rule: QualityRule) -> None:
        """Add a rule for a label."""
        if label not in self.rules:
            self.rules[label] = []
        self.rules[label].append(rule)
    
    def get_rules(self, label: str) -> list[QualityRule]:
        """Get rules for a label."""
        return self.rules.get(label, [])
