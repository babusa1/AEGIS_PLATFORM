"""Clinical Guidelines Connector"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

class GuidelineCategory(str, Enum):
    SCREENING = "screening"
    TREATMENT = "treatment"
    PREVENTION = "prevention"
    MONITORING = "monitoring"
    DIAGNOSIS = "diagnosis"

class EvidenceLevel(str, Enum):
    LEVEL_A = "A"
    LEVEL_B = "B"
    LEVEL_C = "C"

@dataclass
class GuidelineRule:
    rule_id: str
    condition: dict
    action: dict
    priority: int = 0

@dataclass
class ClinicalGuideline:
    guideline_id: str
    name: str
    category: GuidelineCategory
    source: str
    version: str | None = None
    effective_date: datetime | None = None
    conditions: list[str] = field(default_factory=list)
    evidence_level: EvidenceLevel | None = None
    rules: list[GuidelineRule] = field(default_factory=list)
    description: str | None = None

class GuidelinesConnector:
    """Clinical Guidelines Connector."""
    
    def __init__(self, tenant_id: str, source_system: str = "guidelines"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def parse(self, data: dict) -> ClinicalGuideline | None:
        try:
            category = GuidelineCategory(data.get("category", "treatment"))
            evidence = data.get("evidence_level")
            if evidence:
                evidence = EvidenceLevel(evidence)
            eff_date = data.get("effective_date")
            if isinstance(eff_date, str):
                eff_date = datetime.fromisoformat(eff_date)
            rules = [GuidelineRule(r.get("rule_id", ""), r.get("condition", {}),
                r.get("action", {}), r.get("priority", 0)) for r in data.get("rules", [])]
            return ClinicalGuideline(data.get("guideline_id", ""), data.get("name", ""),
                category, data.get("source", ""), data.get("version"), eff_date,
                data.get("conditions", []), evidence, rules, data.get("description"))
        except Exception as e:
            logger.error("Guideline parse failed", error=str(e))
            return None
    
    def transform(self, guideline: ClinicalGuideline):
        vertices, edges = [], []
        gid = f"Guideline/{guideline.guideline_id}"
        vertices.append({"label": "Guideline", "id": gid, "tenant_id": self.tenant_id,
            "source_system": self.source_system, "guideline_id": guideline.guideline_id,
            "name": guideline.name, "category": guideline.category.value,
            "source": guideline.source, "version": guideline.version,
            "conditions": guideline.conditions, "description": guideline.description,
            "evidence_level": guideline.evidence_level.value if guideline.evidence_level else None,
            "created_at": datetime.utcnow().isoformat()})
        for rule in guideline.rules:
            rid = f"GuidelineRule/{rule.rule_id}"
            vertices.append({"label": "GuidelineRule", "id": rid, "tenant_id": self.tenant_id,
                "rule_id": rule.rule_id, "condition": str(rule.condition),
                "action": str(rule.action), "priority": rule.priority,
                "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "HAS_RULE", "from_label": "Guideline", "from_id": gid,
                "to_label": "GuidelineRule", "to_id": rid, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_GUIDELINE = {"guideline_id": "ADA-DM-2024", "name": "ADA Diabetes Standards of Care",
    "category": "treatment", "source": "American Diabetes Association", "version": "2024",
    "effective_date": "2024-01-01", "conditions": ["diabetes", "prediabetes"],
    "evidence_level": "A", "description": "Standards of care for diabetes management",
    "rules": [{"rule_id": "A1C-TARGET", "condition": {"diagnosis": "diabetes"},
        "action": {"target": "HbA1c < 7%"}, "priority": 1}]}
