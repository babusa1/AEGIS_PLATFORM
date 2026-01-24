"""Terminology Service"""
from aegis_terminology.models import Code, CodeSystem

class TerminologyService:
    SNOMED = {"73211009": "Diabetes", "38341003": "Hypertension"}
    LOINC = {"4548-4": "HbA1c", "2160-0": "Creatinine"}
    
    async def lookup(self, code: str, system: CodeSystem) -> Code | None:
        if system == CodeSystem.SNOMED and code in self.SNOMED:
            return Code(code, system, self.SNOMED[code])
        if system == CodeSystem.LOINC and code in self.LOINC:
            return Code(code, system, self.LOINC[code])
        return None
    
    async def validate(self, code: str, system: CodeSystem) -> bool:
        return await self.lookup(code, system) is not None
