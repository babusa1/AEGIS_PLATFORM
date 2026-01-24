"""FHIR Consent Connector"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult

logger = structlog.get_logger(__name__)

class ConsentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"

class ConsentScope(str, Enum):
    TREATMENT = "treatment"
    RESEARCH = "research"
    PATIENT_PRIVACY = "patient-privacy"
    ADR = "adr"

class ConsentAction(str, Enum):
    COLLECT = "collect"
    ACCESS = "access"
    USE = "use"
    DISCLOSE = "disclose"
    CORRECT = "correct"

@dataclass
class ConsentProvision:
    type: str  # permit or deny
    actions: list[ConsentAction]
    purpose: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)

@dataclass
class Consent:
    consent_id: str
    patient_id: str
    status: ConsentStatus
    scope: ConsentScope
    date_time: datetime
    grantor: str | None = None
    grantee: str | None = None
    provisions: list[ConsentProvision] = field(default_factory=list)
    policy_uri: str | None = None

class ConsentConnector(BaseConnector):
    """FHIR Consent Connector."""
    
    def __init__(self, tenant_id: str, source_system: str = "consent"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "consent"
    
    async def parse(self, data: Any) -> ConnectorResult:
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be dict"])
        try:
            consent = self._parse_consent(data)
            if not consent:
                return ConnectorResult(success=False, errors=["Failed to parse"])
            vertices, edges = self._transform(consent)
            return ConnectorResult(success=True, vertices=vertices, edges=edges,
                metadata={"consent_id": consent.consent_id, "status": consent.status.value})
        except Exception as e:
            return ConnectorResult(success=False, errors=[str(e)])
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be dict")
        elif not data.get("patient_id") and not data.get("patient", {}).get("reference"):
            errors.append("Missing patient reference")
        return errors
    
    def _parse_consent(self, data: dict) -> Consent | None:
        try:
            # Handle FHIR format
            if data.get("resourceType") == "Consent":
                patient_ref = data.get("patient", {}).get("reference", "")
                patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
                dt_str = data.get("dateTime", "")
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")) if dt_str else datetime.utcnow()
                scope_code = data.get("scope", {}).get("coding", [{}])[0].get("code", "treatment")
                provisions = []
                for prov in data.get("provision", {}).get("provision", []):
                    actions = [ConsentAction(a.get("coding", [{}])[0].get("code", "access"))
                        for a in prov.get("action", [])]
                    provisions.append(ConsentProvision(prov.get("type", "permit"), actions))
                return Consent(data.get("id", ""), patient_id,
                    ConsentStatus(data.get("status", "active")),
                    ConsentScope(scope_code) if scope_code in [s.value for s in ConsentScope] else ConsentScope.TREATMENT,
                    dt, provisions=provisions, policy_uri=data.get("policyRule", {}).get("uri"))
            # Handle simple format
            dt = data.get("date_time", data.get("dateTime"))
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            else:
                dt = datetime.utcnow()
            provisions = [ConsentProvision(p.get("type", "permit"),
                [ConsentAction(a) for a in p.get("actions", ["access"])],
                p.get("purpose", []), p.get("data_classes", []))
                for p in data.get("provisions", [])]
            return Consent(data.get("consent_id", data.get("id", "")), data.get("patient_id", ""),
                ConsentStatus(data.get("status", "active")),
                ConsentScope(data.get("scope", "treatment")), dt,
                data.get("grantor"), data.get("grantee"), provisions, data.get("policy_uri"))
        except Exception as e:
            logger.error("Consent parse failed", error=str(e))
            return None
    
    def _transform(self, consent: Consent):
        vertices, edges = [], []
        cid = f"Consent/{consent.consent_id}"
        vertices.append(self._create_vertex("Consent", cid, {
            "consent_id": consent.consent_id, "status": consent.status.value,
            "scope": consent.scope.value, "date_time": consent.date_time.isoformat(),
            "grantor": consent.grantor, "grantee": consent.grantee,
            "policy_uri": consent.policy_uri,
            "provision_count": len(consent.provisions)}))
        edges.append(self._create_edge("HAS_CONSENT", "Patient",
            f"Patient/{consent.patient_id}", "Consent", cid))
        for i, prov in enumerate(consent.provisions):
            pid = f"ConsentProvision/{consent.consent_id}-{i}"
            vertices.append(self._create_vertex("ConsentProvision", pid, {
                "type": prov.type, "actions": [a.value for a in prov.actions],
                "purpose": prov.purpose, "data_classes": prov.data_classes}))
            edges.append(self._create_edge("HAS_PROVISION", "Consent", cid,
                "ConsentProvision", pid))
        return vertices, edges

SAMPLE_CONSENT = {"consent_id": "CONSENT-001", "patient_id": "PAT12345",
    "status": "active", "scope": "treatment", "date_time": "2024-01-15T10:00:00",
    "grantor": "PAT12345", "grantee": "Hospital ABC",
    "provisions": [{"type": "permit", "actions": ["access", "use"],
        "purpose": ["treatment"], "data_classes": ["medical-record"]}],
    "policy_uri": "http://hospital.org/consent-policy"}
