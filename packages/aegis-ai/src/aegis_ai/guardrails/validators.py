"""Input/Output Validators"""
from dataclasses import dataclass
from typing import Any
import re


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    sanitized: str | None = None


class InputValidator:
    """Validate and sanitize user inputs."""
    
    MAX_LENGTH = 10000
    
    def validate(self, text: str, context: dict | None = None) -> ValidationResult:
        errors = []
        warnings = []
        
        # Length check
        if len(text) > self.MAX_LENGTH:
            errors.append(f"Input exceeds max length of {self.MAX_LENGTH}")
        
        # Empty check
        if not text.strip():
            errors.append("Input cannot be empty")
        
        # Injection patterns
        if re.search(r'<script|javascript:|on\w+=', text, re.IGNORECASE):
            errors.append("Potential injection detected")
        
        # Prompt injection attempts
        injection_patterns = [
            r'ignore previous instructions',
            r'disregard all prior',
            r'new instructions:',
            r'system prompt',
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append("Potential prompt injection attempt")
                break
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized=text[:self.MAX_LENGTH] if len(errors) == 0 else None
        )


class OutputValidator:
    """Validate AI outputs before returning to user."""
    
    DISCLAIMER = "\n\n*This information is for educational purposes only and should not replace professional medical advice.*"
    
    def validate(self, text: str, context: dict | None = None) -> ValidationResult:
        errors = []
        warnings = []
        sanitized = text
        
        # Check for hallucination markers
        uncertainty_phrases = ["I'm not sure", "I don't know", "I cannot"]
        if any(p in text for p in uncertainty_phrases):
            warnings.append("Response contains uncertainty markers")
        
        # Check for fabricated citations
        if re.search(r'\[\d+\]|\(et al\., \d{4}\)', text):
            warnings.append("Contains citation-like patterns - verify sources")
        
        # Add disclaimer if medical content
        if context and context.get("needs_disclaimer"):
            sanitized = text + self.DISCLAIMER
        
        return ValidationResult(
            valid=True,
            errors=errors,
            warnings=warnings,
            sanitized=sanitized
        )
