"""PHI De-identification - HIPAA Safe Harbor"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import re
import structlog

logger = structlog.get_logger(__name__)


class DeidentifyMethod(str, Enum):
    SAFE_HARBOR = "safe_harbor"
    EXPERT = "expert_determination"
    LIMITED = "limited_dataset"


# HIPAA Safe Harbor 18 identifiers
SAFE_HARBOR_IDENTIFIERS = [
    "name", "address", "dates", "phone", "fax", "email",
    "ssn", "mrn", "health_plan_id", "account_number",
    "certificate_license", "vehicle_id", "device_id",
    "url", "ip_address", "biometric", "photo", "other_unique"
]


@dataclass
class DeidentifyResult:
    original_length: int
    redacted_count: int
    method: DeidentifyMethod
    text: str
    redactions: list[dict] = field(default_factory=list)


class DeidentificationEngine:
    """
    PHI De-identification using HIPAA Safe Harbor.
    
    HITRUST 09.p: Protection of records
    SOC 2 Confidentiality: Data minimization
    """
    
    PATTERNS = {
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "mrn": r'\bMRN[:\s#]*\d{6,}\b',
        "date": r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        "ip": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "zip": r'\b\d{5}(-\d{4})?\b',
        "account": r'\b[A-Z]{2}\d{6,}\b',
    }
    
    def __init__(self, method: DeidentifyMethod = DeidentifyMethod.SAFE_HARBOR):
        self.method = method
        self._custom_patterns: dict[str, str] = {}
    
    def add_pattern(self, name: str, pattern: str):
        """Add custom pattern to detect."""
        self._custom_patterns[name] = pattern
    
    def deidentify(self, text: str, preserve_length: bool = False) -> DeidentifyResult:
        """De-identify PHI from text using Safe Harbor method."""
        redactions = []
        result = text
        
        # Apply all patterns
        all_patterns = {**self.PATTERNS, **self._custom_patterns}
        
        for identifier, pattern in all_patterns.items():
            matches = list(re.finditer(pattern, result, re.IGNORECASE))
            for match in reversed(matches):
                original = match.group()
                replacement = self._get_replacement(identifier, original, preserve_length)
                redactions.append({
                    "type": identifier,
                    "start": match.start(),
                    "end": match.end(),
                    "original_length": len(original)
                })
                result = result[:match.start()] + replacement + result[match.end():]
        
        # Detect potential names (simple heuristic)
        name_matches = re.finditer(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', result)
        for match in reversed(list(name_matches)):
            original = match.group()
            if not self._is_common_term(original):
                replacement = "[NAME]" if not preserve_length else "X" * len(original)
                redactions.append({"type": "name", "start": match.start(), "end": match.end()})
                result = result[:match.start()] + replacement + result[match.end():]
        
        logger.info("De-identified text", redactions=len(redactions), method=self.method.value)
        
        return DeidentifyResult(
            original_length=len(text),
            redacted_count=len(redactions),
            method=self.method,
            text=result,
            redactions=redactions
        )
    
    def _get_replacement(self, identifier: str, original: str, preserve_length: bool) -> str:
        """Get replacement text for identifier."""
        if preserve_length:
            return "X" * len(original)
        
        replacements = {
            "ssn": "[SSN]",
            "phone": "[PHONE]",
            "email": "[EMAIL]",
            "mrn": "[MRN]",
            "date": "[DATE]",
            "ip": "[IP]",
            "zip": "[ZIP]",
            "account": "[ACCOUNT]",
            "name": "[NAME]",
        }
        return replacements.get(identifier, "[REDACTED]")
    
    def _is_common_term(self, text: str) -> bool:
        """Check if text is a common medical term, not a name."""
        common = ["Type Diabetes", "Blood Pressure", "Heart Rate", "New York",
                 "United States", "Primary Care", "Emergency Room"]
        return text in common
    
    def deidentify_record(self, record: dict, fields_to_process: list[str] | None = None) -> dict:
        """De-identify specific fields in a record."""
        result = record.copy()
        fields = fields_to_process or list(record.keys())
        
        for field in fields:
            if field in result and isinstance(result[field], str):
                deident = self.deidentify(result[field])
                result[field] = deident.text
        
        return result
