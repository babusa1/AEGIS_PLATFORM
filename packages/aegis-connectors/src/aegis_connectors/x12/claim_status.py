"""X12 276/277 Claim Status Connector"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class ClaimStatusCode(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"
    FINALIZED = "finalized"
    DENIED = "denied"

@dataclass
class ClaimStatusInfo:
    claim_id: str
    status: ClaimStatusCode
    status_date: datetime | None
    payer_claim_id: str | None = None
    total_charge: float | None = None
    total_paid: float | None = None
    denial_reason: str | None = None
    denial_code: str | None = None

@dataclass
class ClaimStatusResponse:
    transaction_id: str
    patient_id: str
    payer_id: str
    payer_name: str
    claims: list[ClaimStatusInfo] = field(default_factory=list)

class X12ClaimStatusParser:
    STATUS_MAP = {"A0": ClaimStatusCode.ACCEPTED, "A1": ClaimStatusCode.ACCEPTED,
        "A2": ClaimStatusCode.ACCEPTED, "A3": ClaimStatusCode.REJECTED, "A4": ClaimStatusCode.DENIED,
        "P0": ClaimStatusCode.PENDING, "F0": ClaimStatusCode.FINALIZED}
    
    def parse(self, data: dict) -> ClaimStatusResponse | None:
        try:
            claims = []
            for c in data.get("claims", []):
                status = ClaimStatusCode(c.get("status", "pending"))
                status_date = c.get("status_date")
                if isinstance(status_date, str):
                    status_date = datetime.fromisoformat(status_date)
                claims.append(ClaimStatusInfo(c.get("claim_id", ""), status, status_date,
                    c.get("payer_claim_id"), c.get("total_charge"), c.get("total_paid"),
                    c.get("denial_reason"), c.get("denial_code")))
            return ClaimStatusResponse(data.get("transaction_id", ""), data.get("patient_id", ""),
                data.get("payer_id", ""), data.get("payer_name", ""), claims)
        except Exception as e:
            logger.error("Claim status parse failed", error=str(e))
            return None

class X12ClaimStatusConnector:
    def __init__(self, tenant_id: str, source_system: str = "x12-status"):
        self.tenant_id = tenant_id
        self.source_system = source_system
        self.parser = X12ClaimStatusParser()
    
    def parse(self, data: dict):
        resp = self.parser.parse(data)
        return self.transform(resp) if resp else None
    
    def transform(self, r: ClaimStatusResponse):
        vertices, edges = [], []
        for c in r.claims:
            status_id = f"ClaimStatus/{c.claim_id}-{r.transaction_id}"
            vertices.append({"label": "ClaimStatus", "id": status_id, "tenant_id": self.tenant_id,
                "claim_id": c.claim_id, "status": c.status.value, "payer_claim_id": c.payer_claim_id,
                "status_date": c.status_date.isoformat() if c.status_date else None,
                "total_charge": c.total_charge, "total_paid": c.total_paid,
                "denial_reason": c.denial_reason, "denial_code": c.denial_code,
                "created_at": datetime.utcnow().isoformat()})
            edges.append({"label": "HAS_STATUS", "from_label": "Claim", "from_id": f"Claim/{c.claim_id}",
                "to_label": "ClaimStatus", "to_id": status_id, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_CLAIM_STATUS = {"transaction_id": "STATUS-001", "patient_id": "PAT12345",
    "payer_id": "BCBS001", "payer_name": "Blue Cross",
    "claims": [{"claim_id": "CLM-001", "status": "denied", "status_date": "2024-01-15",
        "payer_claim_id": "BCBS-CLM-001", "total_charge": 5000.00, "total_paid": 0,
        "denial_reason": "Prior authorization required", "denial_code": "PR01"}]}
