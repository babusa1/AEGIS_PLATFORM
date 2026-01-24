"""Terminology Models"""
from dataclasses import dataclass
from enum import Enum

class CodeSystem(str, Enum):
    SNOMED = "snomed"
    LOINC = "loinc"
    ICD10 = "icd10"
    RXNORM = "rxnorm"

@dataclass
class Code:
    code: str
    system: CodeSystem
    display: str | None = None
