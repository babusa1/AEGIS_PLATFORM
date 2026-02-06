"""
PHI (Protected Health Information) Detection and Redaction

Automatically detects and redacts PHI from logs and outputs for HIPAA compliance.
Uses Microsoft Presidio or spaCy for entity recognition.
"""

from typing import List, Dict, Any, Optional
import re
import structlog

logger = structlog.get_logger(__name__)

# Try to import Presidio (preferred) or spaCy
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    try:
        import spacy
        SPACY_AVAILABLE = True
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            SPACY_AVAILABLE = False
            nlp = None
    except ImportError:
        SPACY_AVAILABLE = False
        nlp = None


class PHIDetector:
    """
    PHI Detection and Redaction.
    
    Detects:
    - Names (patient, provider)
    - Dates (birth dates, service dates)
    - Phone numbers
    - Email addresses
    - SSN
    - Medical record numbers (MRN)
    - Addresses
    - Account numbers
    """
    
    def __init__(self):
        self.analyzer = None
        self.anonymizer = None
        
        if PRESIDIO_AVAILABLE:
            try:
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
                logger.info("PHI detection initialized with Presidio")
            except Exception as e:
                logger.warning("Presidio initialization failed", error=str(e))
                self._init_fallback()
        else:
            self._init_fallback()
    
    def _init_fallback(self):
        """Initialize fallback PHI detection using regex patterns."""
        logger.info("Using regex-based PHI detection (fallback)")
        
        # Common PHI patterns
        self.patterns = {
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "mrn": re.compile(r'\bMRN\s*:?\s*\d+\b', re.IGNORECASE),
            "date": re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            "account": re.compile(r'\bAccount\s*:?\s*\d+\b', re.IGNORECASE),
        }
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PHI in text.
        
        Returns:
            List of detected entities with type, start, end, value
        """
        if not text:
            return []
        
        entities = []
        
        # Use Presidio if available
        if self.analyzer:
            try:
                results = self.analyzer.analyze(text=text, language="en")
                for result in results:
                    entities.append({
                        "type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "value": text[result.start:result.end],
                        "score": result.score,
                    })
                return entities
            except Exception as e:
                logger.warning("Presidio detection failed, using fallback", error=str(e))
        
        # Fallback: Regex-based detection
        for entity_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                entities.append({
                    "type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                    "score": 0.9,  # High confidence for regex matches
                })
        
        # Remove overlapping entities (keep longest)
        entities = self._deduplicate_entities(entities)
        
        return entities
    
    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact PHI from text.
        
        Args:
            text: Text to redact
            replacement: Replacement string (default: "[REDACTED]")
            
        Returns:
            Text with PHI redacted
        """
        if not text:
            return text
        
        # Use Presidio anonymizer if available
        if self.anonymizer:
            try:
                entities = self.detect(text)
                if not entities:
                    return text
                
                # Convert to Presidio format
                from presidio_analyzer import RecognizerResult
                analyzer_results = [
                    RecognizerResult(
                        entity_type=e["type"],
                        start=e["start"],
                        end=e["end"],
                        score=e["score"],
                    )
                    for e in entities
                ]
                
                anonymized = self.anonymizer.anonymize(
                    text=text,
                    analyzer_results=analyzer_results,
                )
                return anonymized.text
            except Exception as e:
                logger.warning("Presidio redaction failed, using fallback", error=str(e))
        
        # Fallback: Regex-based redaction
        redacted_text = text
        entities = self.detect(text)
        
        # Sort by start position (descending) to redact from end to start
        entities.sort(key=lambda x: x["start"], reverse=True)
        
        for entity in entities:
            start = entity["start"]
            end = entity["end"]
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
        
        return redacted_text
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping entities, keeping the longest."""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda x: x["start"])
        
        deduplicated = []
        for entity in entities:
            # Check if overlaps with any existing entity
            overlaps = False
            for existing in deduplicated:
                if not (entity["end"] <= existing["start"] or entity["start"] >= existing["end"]):
                    # Overlaps - keep the longer one
                    entity_len = entity["end"] - entity["start"]
                    existing_len = existing["end"] - existing["start"]
                    if entity_len > existing_len:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated


# Global PHI detector instance
_phi_detector: Optional[PHIDetector] = None


def get_phi_detector() -> PHIDetector:
    """Get global PHI detector instance."""
    global _phi_detector
    if _phi_detector is None:
        _phi_detector = PHIDetector()
    return _phi_detector


def redact_phi(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Convenience function to redact PHI from text.
    
    Usage:
        safe_text = redact_phi(log_message)
        logger.info("Patient data", data=safe_text)
    """
    detector = get_phi_detector()
    return detector.redact(text, replacement)


def detect_phi(text: str) -> List[Dict[str, Any]]:
    """
    Convenience function to detect PHI in text.
    
    Returns:
        List of detected PHI entities
    """
    detector = get_phi_detector()
    return detector.detect(text)
