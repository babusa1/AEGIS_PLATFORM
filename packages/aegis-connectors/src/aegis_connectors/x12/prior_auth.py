"""
X12 278 Prior Authorization Connector

Parses prior authorization request/response transactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class AuthStatus(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"
    MODIFIED = "modified"
    CANCELLED = "cancelled"


class ServiceCategory(str, Enum):
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    SURGERY = "surgery"
    IMAGING = "imaging"
    DME = "dme"
    THERAPY = "therapy"
    MEDICATION = "medication"
    OTHER = "other"


@dataclass
class AuthService:
    """Service being authorized."""
    service_code: str
    service_description: str
    category: ServiceCategory
    quantity: int | None = None
    unit: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None


@dataclass
class PriorAuthResponse:
    """Parsed 278 response."""
    auth_id: str
    reference_number: str | None
    patient_id: str
    provider_id: str
    payer_id: str
    status: AuthStatus
    decision_date: datetime | None
    effective_date: datetime | None
    expiration_date: datetime | None
    services: list[AuthService] = field(default_factory=list)
    denial_reason: str | None = None
    notes: str | None = None


class X12PriorAuthParser:
    """Parse X12 278 transactions."""
    
    STATUS_CODES = {
        "A1": AuthStatus.APPROVED,
        "A2": AuthStatus.APPROVED,  # Approved with modification
        "A3": AuthStatus.DENIED,
        "A4": AuthStatus.PENDING,
        "A6": AuthStatus.CANCELLED,
    }
    
    def parse(self, data: str | dict) -> PriorAuthResponse | None:
        """Parse 278 response."""
        try:
            if isinstance(data, dict):
                return self._parse_dict(data)
            else:
                return self._parse_edi(data)
        except Exception as e:
            logger.error("Failed to parse 278", error=str(e))
            return None
    
    def _parse_dict(self, data: dict) -> PriorAuthResponse:
        """Parse from dict format."""
        # Parse services
        services = []
        for s in data.get("services", []):
            category = ServiceCategory(s.get("category", "other"))
            from_date = s.get("from_date")
            if isinstance(from_date, str):
                from_date = datetime.fromisoformat(from_date)
            to_date = s.get("to_date")
            if isinstance(to_date, str):
                to_date = datetime.fromisoformat(to_date)
            
            services.append(AuthService(
                service_code=s.get("code", ""),
                service_description=s.get("description", ""),
                category=category,
                quantity=s.get("quantity"),
                unit=s.get("unit"),
                from_date=from_date,
                to_date=to_date,
            ))
        
        # Parse dates
        decision_date = data.get("decision_date")
        if isinstance(decision_date, str):
            decision_date = datetime.fromisoformat(decision_date)
        
        effective_date = data.get("effective_date")
        if isinstance(effective_date, str):
            effective_date = datetime.fromisoformat(effective_date)
        
        expiration_date = data.get("expiration_date")
        if isinstance(expiration_date, str):
            expiration_date = datetime.fromisoformat(expiration_date)
        
        # Parse status
        status_str = data.get("status", "pending")
        status = AuthStatus(status_str) if status_str in [s.value for s in AuthStatus] else AuthStatus.PENDING
        
        return PriorAuthResponse(
            auth_id=data.get("auth_id", ""),
            reference_number=data.get("reference_number"),
            patient_id=data.get("patient_id", ""),
            provider_id=data.get("provider_id", ""),
            payer_id=data.get("payer_id", ""),
            status=status,
            decision_date=decision_date,
            effective_date=effective_date,
            expiration_date=expiration_date,
            services=services,
            denial_reason=data.get("denial_reason"),
            notes=data.get("notes"),
        )
    
    def _parse_edi(self, edi_text: str) -> PriorAuthResponse:
        """Parse raw X12 278 EDI."""
        segments = self._split_segments(edi_text)
        
        auth_id = ""
        reference_number = None
        patient_id = ""
        provider_id = ""
        payer_id = ""
        status = AuthStatus.PENDING
        services = []
        
        for seg in segments:
            elements = seg.split("*")
            seg_id = elements[0] if elements else ""
            
            if seg_id == "BHT":
                auth_id = elements[3] if len(elements) > 3 else ""
            
            elif seg_id == "NM1":
                entity = elements[1] if len(elements) > 1 else ""
                if entity == "PR":  # Payer
                    payer_id = elements[9] if len(elements) > 9 else ""
                elif entity == "1P":  # Provider
                    provider_id = elements[9] if len(elements) > 9 else ""
                elif entity == "IL":  # Patient
                    patient_id = elements[9] if len(elements) > 9 else ""
            
            elif seg_id == "TRN":
                reference_number = elements[2] if len(elements) > 2 else None
            
            elif seg_id == "HCR":
                action_code = elements[1] if len(elements) > 1 else ""
                if action_code in self.STATUS_CODES:
                    status = self.STATUS_CODES[action_code]
            
            elif seg_id == "SV1":
                # Service line
                service_code = ""
                if len(elements) > 1:
                    code_parts = elements[1].split(":")
                    service_code = code_parts[1] if len(code_parts) > 1 else code_parts[0]
                
                services.append(AuthService(
                    service_code=service_code,
                    service_description="",
                    category=ServiceCategory.OTHER,
                ))
        
        return PriorAuthResponse(
            auth_id=auth_id,
            reference_number=reference_number,
            patient_id=patient_id,
            provider_id=provider_id,
            payer_id=payer_id,
            status=status,
            decision_date=None,
            effective_date=None,
            expiration_date=None,
            services=services,
        )
    
    def _split_segments(self, edi_text: str) -> list[str]:
        """Split EDI into segments."""
        edi_text = edi_text.replace("\n", "").replace("\r", "")
        if "~" in edi_text:
            return [s.strip() for s in edi_text.split("~") if s.strip()]
        return [s.strip() for s in edi_text.split("\n") if s.strip()]


class X12PriorAuthConnector:
    """
    X12 278 Prior Authorization Connector.
    
    Transforms prior auth data into Authorization vertices.
    """
    
    def __init__(self, tenant_id: str, source_system: str = "x12-prior-auth"):
        self.tenant_id = tenant_id
        self.source_system = source_system
        self.parser = X12PriorAuthParser()
    
    def parse(self, data: str | dict) -> tuple[list[dict], list[dict]] | None:
        """Parse and transform prior auth."""
        response = self.parser.parse(data)
        if not response:
            return None
        return self.transform(response)
    
    def transform(self, response: PriorAuthResponse) -> tuple[list[dict], list[dict]]:
        """Transform prior auth to vertices/edges."""
        vertices = []
        edges = []
        
        auth_id = f"Authorization/{response.auth_id}"
        patient_id = f"Patient/{response.patient_id}"
        
        # Create Authorization vertex
        auth_vertex = {
            "label": "Authorization",
            "id": auth_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "auth_id": response.auth_id,
            "reference_number": response.reference_number,
            "provider_id": response.provider_id,
            "payer_id": response.payer_id,
            "status": response.status.value,
            "decision_date": response.decision_date.isoformat() if response.decision_date else None,
            "effective_date": response.effective_date.isoformat() if response.effective_date else None,
            "expiration_date": response.expiration_date.isoformat() if response.expiration_date else None,
            "denial_reason": response.denial_reason,
            "notes": response.notes,
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(auth_vertex)
        
        # Link to patient
        edges.append({
            "label": "HAS_AUTHORIZATION",
            "from_label": "Patient",
            "from_id": patient_id,
            "to_label": "Authorization",
            "to_id": auth_id,
            "tenant_id": self.tenant_id,
        })
        
        # Link to provider
        provider_ref = f"Practitioner/{response.provider_id}"
        edges.append({
            "label": "REQUESTED_BY",
            "from_label": "Authorization",
            "from_id": auth_id,
            "to_label": "Practitioner",
            "to_id": provider_ref,
            "tenant_id": self.tenant_id,
        })
        
        # Create service vertices
        for i, service in enumerate(response.services):
            svc_id = f"AuthorizedService/{response.auth_id}-{i}"
            
            svc_vertex = {
                "label": "AuthorizedService",
                "id": svc_id,
                "tenant_id": self.tenant_id,
                "service_code": service.service_code,
                "description": service.service_description,
                "category": service.category.value,
                "quantity": service.quantity,
                "unit": service.unit,
                "from_date": service.from_date.isoformat() if service.from_date else None,
                "to_date": service.to_date.isoformat() if service.to_date else None,
                "created_at": datetime.utcnow().isoformat(),
            }
            vertices.append(svc_vertex)
            
            edges.append({
                "label": "AUTHORIZES_SERVICE",
                "from_label": "Authorization",
                "from_id": auth_id,
                "to_label": "AuthorizedService",
                "to_id": svc_id,
                "tenant_id": self.tenant_id,
            })
        
        return vertices, edges


# Sample prior auth for testing
SAMPLE_PRIOR_AUTH = {
    "auth_id": "AUTH-001",
    "reference_number": "REF123456",
    "patient_id": "PAT12345",
    "provider_id": "NPI1234567890",
    "payer_id": "BCBS001",
    "status": "approved",
    "decision_date": "2024-01-15",
    "effective_date": "2024-01-20",
    "expiration_date": "2024-04-20",
    "services": [
        {
            "code": "27447",
            "description": "Total Knee Arthroplasty",
            "category": "surgery",
            "quantity": 1,
            "from_date": "2024-01-20",
            "to_date": "2024-01-20",
        },
        {
            "code": "99213",
            "description": "Post-op follow-up visits",
            "category": "outpatient",
            "quantity": 6,
            "unit": "visits",
            "from_date": "2024-01-27",
            "to_date": "2024-04-20",
        },
    ],
    "notes": "Approved for medically necessary knee replacement",
}
