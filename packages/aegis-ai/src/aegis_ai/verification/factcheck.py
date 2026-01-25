"""Fact Checking"""
from dataclasses import dataclass


@dataclass
class FactCheckResult:
    claim: str
    verified: bool
    confidence: float
    source: str | None = None


class FactChecker:
    def __init__(self, graph=None):
        self._graph = graph
    
    async def verify(self, claim: str, patient_id: str | None = None) -> FactCheckResult:
        if not self._graph:
            return FactCheckResult(claim, False, 0.0, "No graph")
        return FactCheckResult(claim, False, 0.5, "Pending verification")
    
    def extract_claims(self, text: str) -> list[str]:
        claims = []
        keywords = ["has", "diagnosed", "prescribed", "taking"]
        for sentence in text.split("."):
            if any(kw in sentence.lower() for kw in keywords):
                claims.append(sentence.strip())
        return claims[:5]
