"""
PHI Detection and Redaction

HIPAA-compliant PHI detection:
- Pattern-based detection (SSN, MRN, dates, etc.)
- NER-based detection (names, addresses)
- Configurable redaction strategies
- Logging integration
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import re
import hashlib

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# PHI Types (HIPAA 18 Identifiers)
# =============================================================================

class PHIType(str, Enum):
    """
    HIPAA 18 PHI Identifiers.
    
    These are the 18 types of information that constitute PHI under HIPAA.
    """
    # Direct identifiers
    NAME = "name"
    SSN = "ssn"
    MRN = "mrn"
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    
    # Geographic
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    ZIP = "zip"
    
    # Dates
    DOB = "dob"
    ADMISSION_DATE = "admission_date"
    DISCHARGE_DATE = "discharge_date"
    DEATH_DATE = "death_date"
    DATE = "date"  # Any date
    AGE_OVER_89 = "age_over_89"
    
    # Numbers
    ACCOUNT_NUMBER = "account_number"
    LICENSE_NUMBER = "license_number"
    VEHICLE_ID = "vehicle_id"
    DEVICE_ID = "device_id"
    
    # Digital
    IP_ADDRESS = "ip_address"
    URL = "url"
    
    # Biometric
    BIOMETRIC = "biometric"
    PHOTO = "photo"
    
    # Other
    OTHER = "other"


class PHIMatch(BaseModel):
    """A detected PHI match."""
    phi_type: PHIType
    text: str
    start: int
    end: int
    confidence: float = 1.0
    
    # Context
    context_before: str = ""
    context_after: str = ""
    
    def __hash__(self):
        return hash((self.phi_type, self.start, self.end))


class RedactionStrategy(str, Enum):
    """Redaction strategies for PHI."""
    MASK = "mask"  # Replace with [REDACTED]
    HASH = "hash"  # Replace with hash
    CATEGORY = "category"  # Replace with [PHI_TYPE]
    REMOVE = "remove"  # Remove entirely
    PARTIAL = "partial"  # Partial masking (e.g., ***-**-1234)
    FAKE = "fake"  # Replace with fake data


# =============================================================================
# Pattern Definitions
# =============================================================================

# SSN patterns
SSN_PATTERNS = [
    r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # 123-45-6789
    r'\bSSN[:\s#]*\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # SSN: 123-45-6789
]

# MRN patterns (various formats)
MRN_PATTERNS = [
    r'\b(?:MRN|Medical Record Number|Patient ID)[:\s#]*[A-Z0-9]{6,12}\b',
    r'\b[A-Z]{2,3}\d{6,10}\b',  # AA123456
]

# Phone patterns
PHONE_PATTERNS = [
    r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
    r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',  # 123-456-7890
    r'\b(?:phone|tel|fax)[:\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
]

# Email pattern
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Date patterns
DATE_PATTERNS = [
    r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # 01/15/2024
    r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',  # 2024-01-15
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}[\s,]+\d{2,4}\b',
    r'\b\d{1,2}[\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4}\b',
    r'\b(?:DOB|Date of Birth|Birth Date)[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
]

# Address patterns
ADDRESS_PATTERNS = [
    r'\b\d{1,5}\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)\b',
    r'\b(?:P\.?O\.?\s*Box|PO Box)\s+\d+\b',
]

# ZIP code patterns
ZIP_PATTERNS = [
    r'\b\d{5}(?:-\d{4})?\b',  # 12345 or 12345-6789
]

# IP Address
IP_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# URL pattern
URL_PATTERN = r'https?://[^\s<>"{}|\\^`\[\]]+'

# Credit card (for safety - shouldn't be in healthcare but might appear)
CREDIT_CARD_PATTERN = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'

# Account numbers
ACCOUNT_PATTERNS = [
    r'\b(?:Account|Acct)[:\s#]*[A-Z0-9]{8,16}\b',
    r'\b(?:Policy|Member|Subscriber)[:\s#]*[A-Z0-9]{8,16}\b',
]


# =============================================================================
# PHI Detector
# =============================================================================

class PHIDetector:
    """
    Detect PHI (Protected Health Information) in text.
    
    Features:
    - Pattern-based detection for structured identifiers
    - Context-aware detection
    - Configurable sensitivity
    - NER integration (optional)
    """
    
    def __init__(
        self,
        sensitivity: str = "high",  # low, medium, high
        custom_patterns: Dict[PHIType, List[str]] = None,
        use_ner: bool = False,
    ):
        self.sensitivity = sensitivity
        self.custom_patterns = custom_patterns or {}
        self.use_ner = use_ner
        
        # Compile patterns
        self._compiled_patterns = self._compile_patterns()
        
        # Load NER model if requested
        self._ner_model = None
        if use_ner:
            self._load_ner_model()
        
        # Common name prefixes/suffixes for context
        self._name_prefixes = {"mr", "mrs", "ms", "dr", "patient", "name"}
        self._name_suffixes = {"jr", "sr", "ii", "iii", "md", "rn", "np"}
    
    def _compile_patterns(self) -> Dict[PHIType, List[re.Pattern]]:
        """Compile all regex patterns."""
        patterns = {
            PHIType.SSN: [re.compile(p, re.IGNORECASE) for p in SSN_PATTERNS],
            PHIType.MRN: [re.compile(p, re.IGNORECASE) for p in MRN_PATTERNS],
            PHIType.PHONE: [re.compile(p, re.IGNORECASE) for p in PHONE_PATTERNS],
            PHIType.EMAIL: [re.compile(EMAIL_PATTERN, re.IGNORECASE)],
            PHIType.DATE: [re.compile(p, re.IGNORECASE) for p in DATE_PATTERNS],
            PHIType.ADDRESS: [re.compile(p, re.IGNORECASE) for p in ADDRESS_PATTERNS],
            PHIType.ZIP: [re.compile(p) for p in ZIP_PATTERNS],
            PHIType.IP_ADDRESS: [re.compile(IP_PATTERN)],
            PHIType.URL: [re.compile(URL_PATTERN)],
            PHIType.ACCOUNT_NUMBER: [re.compile(p, re.IGNORECASE) for p in ACCOUNT_PATTERNS],
        }
        
        # Add custom patterns
        for phi_type, custom in self.custom_patterns.items():
            if phi_type not in patterns:
                patterns[phi_type] = []
            patterns[phi_type].extend([re.compile(p, re.IGNORECASE) for p in custom])
        
        return patterns
    
    def _load_ner_model(self):
        """Load NER model for name/entity detection."""
        try:
            import spacy
            self._ner_model = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy NER model")
        except ImportError:
            logger.warning("spaCy not installed, NER disabled")
        except Exception as e:
            logger.warning(f"Failed to load NER model: {e}")
    
    def detect(self, text: str) -> List[PHIMatch]:
        """
        Detect all PHI in text.
        
        Returns list of PHI matches with type, location, and confidence.
        """
        matches = []
        
        # Pattern-based detection
        for phi_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Get context
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    
                    phi_match = PHIMatch(
                        phi_type=phi_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=self._calculate_confidence(phi_type, match.group(), text),
                        context_before=text[start:match.start()],
                        context_after=text[match.end():end],
                    )
                    matches.append(phi_match)
        
        # NER-based detection for names and locations
        if self._ner_model:
            ner_matches = self._detect_with_ner(text)
            matches.extend(ner_matches)
        
        # Name detection (heuristic)
        if self.sensitivity in ["medium", "high"]:
            name_matches = self._detect_names_heuristic(text)
            matches.extend(name_matches)
        
        # Deduplicate overlapping matches
        matches = self._deduplicate_matches(matches)
        
        # Filter by confidence based on sensitivity
        min_confidence = {"low": 0.8, "medium": 0.6, "high": 0.4}.get(self.sensitivity, 0.6)
        matches = [m for m in matches if m.confidence >= min_confidence]
        
        logger.debug(f"Detected {len(matches)} PHI matches")
        return matches
    
    def _calculate_confidence(self, phi_type: PHIType, text: str, full_text: str) -> float:
        """Calculate confidence score for a match."""
        confidence = 0.7  # Base confidence
        
        # SSN is high confidence if it matches format
        if phi_type == PHIType.SSN:
            # Check for context clues
            if any(kw in full_text.lower() for kw in ["ssn", "social security", "ss#"]):
                confidence = 0.95
            else:
                confidence = 0.8
        
        # MRN with label is high confidence
        elif phi_type == PHIType.MRN:
            if any(kw in full_text.lower() for kw in ["mrn", "medical record", "patient id"]):
                confidence = 0.9
            else:
                confidence = 0.6
        
        # Email is high confidence
        elif phi_type == PHIType.EMAIL:
            confidence = 0.95
        
        # Phone with context
        elif phi_type == PHIType.PHONE:
            if any(kw in full_text.lower() for kw in ["phone", "tel", "fax", "call"]):
                confidence = 0.9
            else:
                confidence = 0.7
        
        # Dates need context to be PHI
        elif phi_type == PHIType.DATE:
            if any(kw in full_text.lower() for kw in ["dob", "birth", "admit", "discharge", "death"]):
                confidence = 0.85
            else:
                confidence = 0.5  # Many dates are not PHI
        
        return confidence
    
    def _detect_with_ner(self, text: str) -> List[PHIMatch]:
        """Detect names and locations using NER."""
        if not self._ner_model:
            return []
        
        matches = []
        doc = self._ner_model(text)
        
        for ent in doc.ents:
            phi_type = None
            confidence = 0.7
            
            if ent.label_ == "PERSON":
                phi_type = PHIType.NAME
                confidence = 0.85
            elif ent.label_ in ["GPE", "LOC"]:  # Geographic/Location
                phi_type = PHIType.ADDRESS
                confidence = 0.6
            elif ent.label_ == "DATE":
                phi_type = PHIType.DATE
                confidence = 0.5  # Dates from NER need verification
            
            if phi_type:
                matches.append(PHIMatch(
                    phi_type=phi_type,
                    text=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence,
                ))
        
        return matches
    
    def _detect_names_heuristic(self, text: str) -> List[PHIMatch]:
        """Detect names using heuristics when NER not available."""
        matches = []
        
        # Pattern: Title + Capitalized words
        name_pattern = r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Patient)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        for match in re.finditer(name_pattern, text):
            matches.append(PHIMatch(
                phi_type=PHIType.NAME,
                text=match.group(1),
                start=match.start(1),
                end=match.end(1),
                confidence=0.75,
            ))
        
        # Pattern: "Name:" or "Patient Name:" followed by text
        label_pattern = r'(?:Patient\s+)?Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        for match in re.finditer(label_pattern, text, re.IGNORECASE):
            matches.append(PHIMatch(
                phi_type=PHIType.NAME,
                text=match.group(1),
                start=match.start(1),
                end=match.end(1),
                confidence=0.85,
            ))
        
        return matches
    
    def _deduplicate_matches(self, matches: List[PHIMatch]) -> List[PHIMatch]:
        """Remove overlapping matches, keeping highest confidence."""
        if not matches:
            return []
        
        # Sort by start position, then by confidence (descending)
        matches.sort(key=lambda m: (m.start, -m.confidence))
        
        deduplicated = []
        last_end = -1
        
        for match in matches:
            if match.start >= last_end:
                deduplicated.append(match)
                last_end = match.end
            elif match.confidence > deduplicated[-1].confidence:
                # Higher confidence match overlaps - replace
                deduplicated[-1] = match
                last_end = match.end
        
        return deduplicated
    
    def contains_phi(self, text: str) -> bool:
        """Quick check if text contains any PHI."""
        matches = self.detect(text)
        return len(matches) > 0
    
    def get_phi_types(self, text: str) -> Set[PHIType]:
        """Get set of PHI types found in text."""
        matches = self.detect(text)
        return {m.phi_type for m in matches}


# =============================================================================
# PHI Redactor
# =============================================================================

class PHIRedactor:
    """
    Redact PHI from text.
    
    Features:
    - Multiple redaction strategies
    - Consistent replacement (same PHI = same replacement)
    - Reversible redaction (with key)
    """
    
    def __init__(
        self,
        detector: PHIDetector = None,
        default_strategy: RedactionStrategy = RedactionStrategy.MASK,
        type_strategies: Dict[PHIType, RedactionStrategy] = None,
    ):
        self.detector = detector or PHIDetector()
        self.default_strategy = default_strategy
        self.type_strategies = type_strategies or {}
        
        # For consistent replacement
        self._replacement_map: Dict[str, str] = {}
        
        # For reversible redaction
        self._redaction_key: Dict[str, str] = {}
    
    def redact(self, text: str, return_matches: bool = False) -> str | Tuple[str, List[PHIMatch]]:
        """
        Redact PHI from text.
        
        Args:
            text: Text to redact
            return_matches: If True, also return list of matches
            
        Returns:
            Redacted text (and optionally matches)
        """
        matches = self.detector.detect(text)
        
        if not matches:
            return (text, []) if return_matches else text
        
        # Sort by position (reverse order for replacement)
        matches.sort(key=lambda m: m.start, reverse=True)
        
        redacted = text
        for match in matches:
            replacement = self._get_replacement(match)
            redacted = redacted[:match.start] + replacement + redacted[match.end:]
            
            # Store for reversibility
            self._redaction_key[replacement] = match.text
        
        return (redacted, matches) if return_matches else redacted
    
    def _get_replacement(self, match: PHIMatch) -> str:
        """Get replacement text for a PHI match."""
        strategy = self.type_strategies.get(match.phi_type, self.default_strategy)
        
        # Check if we've seen this exact PHI before
        if match.text in self._replacement_map:
            return self._replacement_map[match.text]
        
        if strategy == RedactionStrategy.MASK:
            replacement = "[REDACTED]"
        
        elif strategy == RedactionStrategy.HASH:
            hash_val = hashlib.sha256(match.text.encode()).hexdigest()[:8]
            replacement = f"[HASH:{hash_val}]"
        
        elif strategy == RedactionStrategy.CATEGORY:
            replacement = f"[{match.phi_type.value.upper()}]"
        
        elif strategy == RedactionStrategy.REMOVE:
            replacement = ""
        
        elif strategy == RedactionStrategy.PARTIAL:
            replacement = self._partial_mask(match)
        
        elif strategy == RedactionStrategy.FAKE:
            replacement = self._generate_fake(match)
        
        else:
            replacement = "[REDACTED]"
        
        # Store for consistent replacement
        self._replacement_map[match.text] = replacement
        
        return replacement
    
    def _partial_mask(self, match: PHIMatch) -> str:
        """Partially mask PHI (e.g., ***-**-1234)."""
        text = match.text
        
        if match.phi_type == PHIType.SSN:
            # Keep last 4 digits
            return "***-**-" + text[-4:]
        
        elif match.phi_type == PHIType.PHONE:
            # Keep area code
            digits = re.sub(r'\D', '', text)
            return f"({digits[:3]}) ***-****"
        
        elif match.phi_type == PHIType.EMAIL:
            # Keep domain
            parts = text.split('@')
            return f"***@{parts[1]}" if len(parts) == 2 else "[EMAIL]"
        
        elif match.phi_type == PHIType.NAME:
            # Keep first initial
            parts = text.split()
            if parts:
                return parts[0][0] + ". " + "*" * 5
            return "[NAME]"
        
        else:
            # Generic partial mask
            if len(text) > 4:
                return text[0] + "*" * (len(text) - 2) + text[-1]
            return "*" * len(text)
    
    def _generate_fake(self, match: PHIMatch) -> str:
        """Generate fake replacement data."""
        # Use consistent fakes based on hash
        hash_seed = int(hashlib.md5(match.text.encode()).hexdigest()[:8], 16)
        
        if match.phi_type == PHIType.NAME:
            names = ["John Smith", "Jane Doe", "Patient A", "Patient B"]
            return names[hash_seed % len(names)]
        
        elif match.phi_type == PHIType.SSN:
            return "000-00-0000"
        
        elif match.phi_type == PHIType.PHONE:
            return "(555) 000-0000"
        
        elif match.phi_type == PHIType.EMAIL:
            return "patient@example.com"
        
        elif match.phi_type == PHIType.DATE:
            return "01/01/2000"
        
        elif match.phi_type == PHIType.ADDRESS:
            return "123 Main Street"
        
        elif match.phi_type == PHIType.ZIP:
            return "00000"
        
        else:
            return f"[{match.phi_type.value.upper()}]"
    
    def get_redaction_map(self) -> Dict[str, str]:
        """Get map of redactions for reversibility."""
        return self._redaction_key.copy()
    
    def clear_maps(self):
        """Clear replacement and redaction maps."""
        self._replacement_map.clear()
        self._redaction_key.clear()


# =============================================================================
# Logging Integration
# =============================================================================

class PHISafeLogger:
    """
    Logger wrapper that automatically redacts PHI.
    
    Usage:
        logger = PHISafeLogger()
        logger.info("Patient John Smith has SSN 123-45-6789")
        # Logs: "Patient [NAME] has SSN [REDACTED]"
    """
    
    def __init__(
        self,
        base_logger=None,
        redactor: PHIRedactor = None,
    ):
        self.base_logger = base_logger or structlog.get_logger("phi_safe")
        self.redactor = redactor or PHIRedactor()
    
    def _safe_log(self, level: str, message: str, **kwargs):
        """Log with PHI redaction."""
        safe_message = self.redactor.redact(message)
        
        # Also redact any string kwargs
        safe_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                safe_kwargs[key] = self.redactor.redact(value)
            else:
                safe_kwargs[key] = value
        
        getattr(self.base_logger, level)(safe_message, **safe_kwargs)
    
    def debug(self, message: str, **kwargs):
        self._safe_log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._safe_log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._safe_log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._safe_log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._safe_log("critical", message, **kwargs)


# =============================================================================
# Convenience Functions
# =============================================================================

_default_detector: Optional[PHIDetector] = None
_default_redactor: Optional[PHIRedactor] = None


def get_phi_detector() -> PHIDetector:
    """Get default PHI detector."""
    global _default_detector
    if _default_detector is None:
        _default_detector = PHIDetector()
    return _default_detector


def get_phi_redactor() -> PHIRedactor:
    """Get default PHI redactor."""
    global _default_redactor
    if _default_redactor is None:
        _default_redactor = PHIRedactor()
    return _default_redactor


def detect_phi(text: str) -> List[PHIMatch]:
    """Detect PHI in text using default detector."""
    return get_phi_detector().detect(text)


def redact_phi(text: str) -> str:
    """Redact PHI from text using default redactor."""
    return get_phi_redactor().redact(text)


def contains_phi(text: str) -> bool:
    """Check if text contains PHI."""
    return get_phi_detector().contains_phi(text)
