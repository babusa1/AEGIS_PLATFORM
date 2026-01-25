"""AI Decision Explainability"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class ExplanationType(str, Enum):
    CLINICAL = "clinical"
    TECHNICAL = "technical"
    PATIENT = "patient"  # Patient-friendly
    AUDIT = "audit"


@dataclass
class Factor:
    name: str
    value: Any
    weight: float
    contribution: str  # positive, negative, neutral


@dataclass
class Explanation:
    decision: str
    confidence: float
    explanation_type: ExplanationType
    summary: str
    factors: list[Factor] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class Explainer:
    """
    Generate explanations for AI decisions.
    
    HITRUST 09.s: Record of data processing
    SOC 2 Processing Integrity: Explainable AI decisions
    """
    
    def __init__(self):
        self._templates = {
            ExplanationType.CLINICAL: self._clinical_template,
            ExplanationType.PATIENT: self._patient_template,
            ExplanationType.TECHNICAL: self._technical_template,
            ExplanationType.AUDIT: self._audit_template,
        }
    
    def explain(self, decision: str, factors: list[Factor],
               reasoning: list[str], confidence: float,
               explanation_type: ExplanationType = ExplanationType.CLINICAL) -> Explanation:
        """Generate an explanation for a decision."""
        template_func = self._templates.get(explanation_type, self._clinical_template)
        summary = template_func(decision, factors, reasoning)
        
        return Explanation(
            decision=decision,
            confidence=confidence,
            explanation_type=explanation_type,
            summary=summary,
            factors=factors,
            reasoning_chain=reasoning
        )
    
    def _clinical_template(self, decision: str, factors: list[Factor], reasoning: list[str]) -> str:
        """Generate clinical explanation."""
        lines = [f"**Decision**: {decision}\n"]
        
        if factors:
            lines.append("**Key Factors**:")
            for f in sorted(factors, key=lambda x: abs(x.weight), reverse=True)[:5]:
                sign = "+" if f.contribution == "positive" else "-" if f.contribution == "negative" else "~"
                lines.append(f"  {sign} {f.name}: {f.value}")
        
        if reasoning:
            lines.append("\n**Reasoning**:")
            for i, step in enumerate(reasoning, 1):
                lines.append(f"  {i}. {step}")
        
        return "\n".join(lines)
    
    def _patient_template(self, decision: str, factors: list[Factor], reasoning: list[str]) -> str:
        """Generate patient-friendly explanation."""
        lines = [f"Based on your health information, we recommend: {decision}\n"]
        
        if factors:
            positive = [f for f in factors if f.contribution == "positive"]
            if positive:
                lines.append("This is based on:")
                for f in positive[:3]:
                    lines.append(f"  - {f.name}")
        
        lines.append("\nPlease discuss this with your healthcare provider.")
        return "\n".join(lines)
    
    def _technical_template(self, decision: str, factors: list[Factor], reasoning: list[str]) -> str:
        """Generate technical explanation."""
        lines = [f"Decision: {decision}"]
        lines.append(f"Factors: {len(factors)}")
        for f in factors:
            lines.append(f"  - {f.name}: {f.value} (weight={f.weight:.2f}, {f.contribution})")
        lines.append(f"Reasoning steps: {len(reasoning)}")
        return "\n".join(lines)
    
    def _audit_template(self, decision: str, factors: list[Factor], reasoning: list[str]) -> str:
        """Generate audit-ready explanation."""
        lines = [
            f"DECISION: {decision}",
            f"TIMESTAMP: {datetime.utcnow().isoformat()}",
            f"FACTOR_COUNT: {len(factors)}",
            "FACTORS:",
        ]
        for f in factors:
            lines.append(f"  {f.name}|{f.value}|{f.weight}|{f.contribution}")
        lines.append("REASONING:")
        for r in reasoning:
            lines.append(f"  {r}")
        return "\n".join(lines)
    
    def explain_risk_score(self, score: float, components: dict[str, float]) -> Explanation:
        """Explain a risk score calculation."""
        factors = [
            Factor(name=k, value=v, weight=v/score if score > 0 else 0,
                  contribution="positive" if v > 0 else "neutral")
            for k, v in components.items()
        ]
        
        reasoning = [
            f"Total risk score: {score:.2f}",
            f"Calculated from {len(components)} components",
            f"Highest contributor: {max(components.items(), key=lambda x: x[1])[0]}"
        ]
        
        return self.explain(
            decision=f"Risk Score: {score:.2f}",
            factors=factors,
            reasoning=reasoning,
            confidence=0.9,
            explanation_type=ExplanationType.CLINICAL
        )
