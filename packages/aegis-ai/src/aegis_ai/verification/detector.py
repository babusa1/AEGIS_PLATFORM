"""Hallucination Detection"""
from dataclasses import dataclass, field
from enum import Enum
import re


class HallucinationType(str, Enum):
    FACTUAL = "factual"
    ENTITY = "entity"
    NUMERIC = "numeric"


@dataclass
class HallucinationResult:
    detected: bool
    confidence: float
    htype: HallucinationType | None = None
    evidence: list[str] = field(default_factory=list)


class HallucinationDetector:
    def __init__(self):
        self._entities: set[str] = set()
    
    def register_entities(self, entities: list[str]):
        self._entities.update(entities)
    
    def check(self, response: str, context: dict | None = None) -> HallucinationResult:
        # Check numerics
        nums = re.findall(r'\b(\d+)\s*(mg|bpm|mmHg)\b', response)
        for val, unit in nums:
            v = int(val)
            if unit == "bpm" and (v < 20 or v > 300):
                return HallucinationResult(True, 0.8, HallucinationType.NUMERIC,
                    [f"Unrealistic {unit}: {v}"])
            if unit == "mmHg" and (v < 40 or v > 300):
                return HallucinationResult(True, 0.8, HallucinationType.NUMERIC,
                    [f"Unrealistic {unit}: {v}"])
        
        # Check citations
        if re.search(r'\(.*et al\., \d{4}\)', response):
            return HallucinationResult(True, 0.5, HallucinationType.FACTUAL,
                ["Unverified citation"])
        
        return HallucinationResult(False, 0.9)
