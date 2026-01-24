"""Drug Labels Connector - FDA/RxNorm"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class DrugInteraction:
    interacting_drug: str
    severity: str
    description: str

@dataclass
class DrugLabel:
    drug_id: str
    name: str
    generic_name: str | None = None
    rxnorm_code: str | None = None
    ndc_codes: list[str] = field(default_factory=list)
    manufacturer: str | None = None
    dosage_forms: list[str] = field(default_factory=list)
    indications: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    interactions: list[DrugInteraction] = field(default_factory=list)

class DrugLabelConnector:
    """Drug Label Connector for FDA/RxNorm data."""
    
    def __init__(self, tenant_id: str, source_system: str = "drug-labels"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def parse(self, data: dict) -> DrugLabel | None:
        try:
            interactions = [DrugInteraction(i.get("drug", ""), i.get("severity", ""),
                i.get("description", "")) for i in data.get("interactions", [])]
            return DrugLabel(data.get("drug_id", ""), data.get("name", ""),
                data.get("generic_name"), data.get("rxnorm_code"),
                data.get("ndc_codes", []), data.get("manufacturer"),
                data.get("dosage_forms", []), data.get("indications", []),
                data.get("contraindications", []), data.get("warnings", []), interactions)
        except Exception as e:
            logger.error("Drug label parse failed", error=str(e))
            return None
    
    def transform(self, drug: DrugLabel):
        vertices, edges = [], []
        did = f"Drug/{drug.drug_id}"
        vertices.append({"label": "Drug", "id": did, "tenant_id": self.tenant_id,
            "source_system": self.source_system, "drug_id": drug.drug_id,
            "name": drug.name, "generic_name": drug.generic_name,
            "rxnorm_code": drug.rxnorm_code, "ndc_codes": drug.ndc_codes,
            "manufacturer": drug.manufacturer, "dosage_forms": drug.dosage_forms,
            "indications": drug.indications, "contraindications": drug.contraindications,
            "warnings": drug.warnings[:5] if drug.warnings else [],
            "created_at": datetime.utcnow().isoformat()})
        for inter in drug.interactions:
            iid = f"DrugInteraction/{drug.drug_id}-{inter.interacting_drug}"
            vertices.append({"label": "DrugInteraction", "id": iid, "tenant_id": self.tenant_id,
                "drug_a": drug.name, "drug_b": inter.interacting_drug,
                "severity": inter.severity, "description": inter.description,
                "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "HAS_INTERACTION", "from_label": "Drug", "from_id": did,
                "to_label": "DrugInteraction", "to_id": iid, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_DRUG = {"drug_id": "METFORMIN-500", "name": "Metformin", "generic_name": "metformin hydrochloride",
    "rxnorm_code": "6809", "ndc_codes": ["0093-7212-01"], "manufacturer": "Teva",
    "dosage_forms": ["tablet", "extended-release tablet"],
    "indications": ["Type 2 diabetes mellitus"], "contraindications": ["Renal impairment eGFR < 30"],
    "warnings": ["Lactic acidosis risk", "Hold before contrast procedures"],
    "interactions": [{"drug": "alcohol", "severity": "moderate",
        "description": "Increased risk of lactic acidosis"}]}
