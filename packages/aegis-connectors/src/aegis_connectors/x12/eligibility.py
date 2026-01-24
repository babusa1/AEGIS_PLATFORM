"""X12 270/271 Eligibility Connector"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class EligibilityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class BenefitType(str, Enum):
    MEDICAL = "medical"
    DENTAL = "dental"
    PHARMACY = "pharmacy"


@dataclass
class Benefit:
    benefit_type: BenefitType
    in_network: bool = True
    deductible: float | None = None
    copay: float | None = None
    coinsurance: float | None = None
    oop_max: float | None = None


@dataclass
class EligibilityResponse:
    transaction_id: str
    patient_id: str
    subscriber_id: str
    payer_id: str
    payer_name: str
    plan_name: str | None
    group_number: str | None
    status: EligibilityStatus
    effective_date: datetime | None
    benefits: list[Benefit] = field(default_factory=list)


class X12EligibilityParser:
    def parse(self, data: dict) -> EligibilityResponse | None:
        try:
            benefits = [Benefit(BenefitType(b.get("type", "medical")), b.get("in_network", True),
                b.get("deductible"), b.get("copay"), b.get("coinsurance"), b.get("oop_max"))
                for b in data.get("benefits", [])]
            eff = data.get("effective_date")
            eff_date = datetime.fromisoformat(eff) if isinstance(eff, str) else eff
            status = EligibilityStatus(data.get("status", "active"))
            return EligibilityResponse(data.get("transaction_id", ""), data.get("patient_id", ""),
                data.get("subscriber_id", ""), data.get("payer_id", ""), data.get("payer_name", ""),
                data.get("plan_name"), data.get("group_number"), status, eff_date, benefits)
        except Exception as e:
            logger.error("Eligibility parse failed", error=str(e))
            return None


class X12EligibilityConnector:
    def __init__(self, tenant_id: str, source_system: str = "x12-elig"):
        self.tenant_id = tenant_id
        self.source_system = source_system
        self.parser = X12EligibilityParser()
    
    def parse(self, data: dict) -> tuple[list[dict], list[dict]] | None:
        resp = self.parser.parse(data)
        return self.transform(resp) if resp else None
    
    def transform(self, r: EligibilityResponse) -> tuple[list[dict], list[dict]]:
        vertices, edges = [], []
        cov_id = f"Coverage/{r.transaction_id}"
        vertices.append({"label": "Coverage", "id": cov_id, "tenant_id": self.tenant_id,
            "subscriber_id": r.subscriber_id, "payer_id": r.payer_id, "payer_name": r.payer_name,
            "plan_name": r.plan_name, "group_number": r.group_number, "status": r.status.value,
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "created_at": datetime.utcnow().isoformat()})
        edges.append({"label": "HAS_COVERAGE", "from_label": "Patient", "from_id": f"Patient/{r.patient_id}",
            "to_label": "Coverage", "to_id": cov_id, "tenant_id": self.tenant_id})
        for i, b in enumerate(r.benefits):
            bid = f"Benefit/{r.transaction_id}-{i}"
            vertices.append({"label": "Benefit", "id": bid, "tenant_id": self.tenant_id,
                "benefit_type": b.benefit_type.value, "deductible": b.deductible, "copay": b.copay,
                "coinsurance": b.coinsurance, "oop_max": b.oop_max, "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "HAS_BENEFIT", "from_label": "Coverage", "from_id": cov_id,
                "to_label": "Benefit", "to_id": bid, "tenant_id": self.tenant_id})
        return vertices, edges


SAMPLE_ELIGIBILITY = {"transaction_id": "ELIG-001", "patient_id": "PAT12345", "subscriber_id": "SUB98765",
    "payer_id": "BCBS001", "payer_name": "Blue Cross", "plan_name": "PPO Gold", "group_number": "GRP123",
    "status": "active", "effective_date": "2024-01-01",
    "benefits": [{"type": "medical", "deductible": 1500, "copay": 30, "coinsurance": 0.2, "oop_max": 6000}]}
