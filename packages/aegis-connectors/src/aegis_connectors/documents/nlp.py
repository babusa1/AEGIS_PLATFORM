"""NLP Clinical Notes Extraction"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import structlog

logger = structlog.get_logger(__name__)

class EntityType(str, Enum):
    MEDICATION = "medication"
    CONDITION = "condition"
    PROCEDURE = "procedure"

@dataclass
class Entity:
    entity_type: EntityType
    text: str
    normalized: str | None = None

@dataclass
class NLPResult:
    document_id: str
    entities: list[Entity] = field(default_factory=list)
    medications: list[Entity] = field(default_factory=list)
    conditions: list[Entity] = field(default_factory=list)

class ClinicalNLPExtractor:
    MED = r'\b(aspirin|metformin|lisinopril|atorvastatin|omeprazole|insulin|warfarin)\b'
    COND = r'\b(diabetes|hypertension|heart failure|COPD|asthma|pneumonia|CKD|cancer)\b'
    
    def extract(self, text: str, doc_id: str = "") -> NLPResult:
        entities = []
        for m in re.finditer(self.MED, text, re.I):
            entities.append(Entity(EntityType.MEDICATION, m.group(0), m.group(0).lower()))
        for m in re.finditer(self.COND, text, re.I):
            entities.append(Entity(EntityType.CONDITION, m.group(0), m.group(0).lower()))
        seen = set()
        unique = [e for e in entities if (e.entity_type, e.normalized) not in seen and not seen.add((e.entity_type, e.normalized))]
        return NLPResult(doc_id, unique, [e for e in unique if e.entity_type == EntityType.MEDICATION],
            [e for e in unique if e.entity_type == EntityType.CONDITION])

class NLPConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.extractor = ClinicalNLPExtractor()
    
    def transform(self, result: NLPResult, patient_id: str):
        vertices, edges = [], []
        for i, c in enumerate(result.conditions):
            cid = f"Condition/{result.document_id}-{i}"
            vertices.append({"label": "Condition", "id": cid, "tenant_id": self.tenant_id,
                "display": c.text, "extracted_from": "nlp", "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "HAS_CONDITION", "from_label": "Patient",
                "from_id": f"Patient/{patient_id}", "to_label": "Condition", "to_id": cid, "tenant_id": self.tenant_id})
        for i, m in enumerate(result.medications):
            mid = f"MedicationStatement/{result.document_id}-{i}"
            vertices.append({"label": "MedicationStatement", "id": mid, "tenant_id": self.tenant_id,
                "medication_name": m.text, "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "TAKES_MEDICATION", "from_label": "Patient",
                "from_id": f"Patient/{patient_id}", "to_label": "MedicationStatement", "to_id": mid, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_NOTE = "Patient has diabetes and hypertension. Taking metformin and lisinopril."
