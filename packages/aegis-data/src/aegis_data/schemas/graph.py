"""Graph Schema"""
from enum import Enum


class VertexType(str, Enum):
    PATIENT = "Patient"
    CONDITION = "Condition"
    MEDICATION = "Medication"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    PROCEDURE = "Procedure"
    PRACTITIONER = "Practitioner"


class EdgeType(str, Enum):
    HAS_CONDITION = "HAS_CONDITION"
    TAKES_MEDICATION = "TAKES_MEDICATION"
    HAD_ENCOUNTER = "HAD_ENCOUNTER"
    HAS_OBSERVATION = "HAS_OBSERVATION"


class GraphSchema:
    REQUIRED = {
        VertexType.PATIENT: ["id", "tenant_id", "first_name", "last_name"],
        VertexType.CONDITION: ["id", "tenant_id", "patient_id", "code"],
    }
    
    @classmethod
    def validate(cls, vtype: VertexType, data: dict) -> list[str]:
        errors = []
        for prop in cls.REQUIRED.get(vtype, []):
            if prop not in data:
                errors.append(f"Missing: {prop}")
        return errors
