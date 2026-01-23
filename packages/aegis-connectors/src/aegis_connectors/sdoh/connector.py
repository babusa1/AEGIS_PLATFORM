"""
SDOH Connector
"""

from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.sdoh.domains import (
    SDOHDomain,
    SDOHScreening,
    SDOHObservation,
    RiskLevel,
    SDOH_LOINC_CODES,
)

logger = structlog.get_logger(__name__)


class SDOHConnector(BaseConnector):
    """
    SDOH Connector.
    
    Ingests social determinants screening data.
    
    Usage:
        connector = SDOHConnector(tenant_id="hospital-a")
        result = await connector.parse(screening_data)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "sdoh"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "sdoh"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse SDOH screening data."""
        errors = []
        
        if isinstance(data, SDOHScreening):
            screening = data
        elif isinstance(data, dict):
            screening = self._dict_to_screening(data)
            if not screening:
                errors.append("Invalid screening data format")
                return ConnectorResult(success=False, errors=errors)
        else:
            return ConnectorResult(success=False, errors=["Data must be dict or SDOHScreening"])
        
        try:
            vertices, edges = self._transform(screening)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "SDOH parse complete",
            screening_id=screening.screening_id,
            observations=len(screening.observations),
            domains=len(screening.domains_identified),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "screening_id": screening.screening_id,
                "patient_id": screening.patient_id,
                "domains_identified": [d.value for d in screening.domains_identified],
                "overall_risk": screening.overall_risk.value if screening.overall_risk else None,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if isinstance(data, dict):
            if "patient_id" not in data:
                errors.append("Missing patient_id")
            if "screening_date" not in data:
                errors.append("Missing screening_date")
        return errors
    
    def _dict_to_screening(self, data: dict) -> SDOHScreening | None:
        """Convert dict to SDOHScreening."""
        try:
            observations = []
            for obs in data.get("observations", []):
                domain = obs.get("domain")
                if isinstance(domain, str):
                    domain = SDOHDomain(domain)
                
                risk = obs.get("risk_level")
                if isinstance(risk, str):
                    risk = RiskLevel(risk)
                
                observations.append(SDOHObservation(
                    domain=domain,
                    code=obs.get("code", ""),
                    display=obs.get("display", ""),
                    value=obs.get("value", ""),
                    value_code=obs.get("value_code"),
                    risk_level=risk,
                ))
            
            screening_date = data.get("screening_date")
            if isinstance(screening_date, str):
                screening_date = datetime.fromisoformat(screening_date)
            
            overall_risk = data.get("overall_risk")
            if isinstance(overall_risk, str):
                overall_risk = RiskLevel(overall_risk)
            
            return SDOHScreening(
                screening_id=data.get("screening_id", f"SDOH-{datetime.utcnow().timestamp()}"),
                patient_id=data.get("patient_id", ""),
                screening_date=screening_date or datetime.utcnow(),
                screening_tool=data.get("screening_tool", "CUSTOM"),
                observations=observations,
                overall_risk=overall_risk,
                referrals_needed=data.get("referrals_needed", []),
            )
            
        except Exception as e:
            logger.error("Failed to convert dict to screening", error=str(e))
            return None
    
    def _transform(self, screening: SDOHScreening) -> tuple[list[dict], list[dict]]:
        """Transform screening to vertices/edges."""
        vertices = []
        edges = []
        
        # Screening vertex
        screening_id = f"SDOHScreening/{screening.screening_id}"
        patient_id = f"Patient/{screening.patient_id}"
        
        screening_vertex = {
            "label": "SDOHScreening",
            "id": screening_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "screening_id": screening.screening_id,
            "screening_date": screening.screening_date.isoformat(),
            "screening_tool": screening.screening_tool,
            "overall_risk": screening.overall_risk.value if screening.overall_risk else None,
            "domains_identified": [d.value for d in screening.domains_identified],
            "referrals_needed": screening.referrals_needed,
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(screening_vertex)
        
        # Link to patient
        edges.append({
            "label": "HAS_SDOH_SCREENING",
            "from_label": "Patient",
            "from_id": patient_id,
            "to_label": "SDOHScreening",
            "to_id": screening_id,
            "tenant_id": self.tenant_id,
        })
        
        # SDOH Observations
        for i, obs in enumerate(screening.observations):
            obs_id = f"SDOHObservation/{screening.screening_id}-{i}"
            
            obs_vertex = {
                "label": "SDOHObservation",
                "id": obs_id,
                "tenant_id": self.tenant_id,
                "domain": obs.domain.value,
                "code": obs.code,
                "display": obs.display,
                "value": obs.value,
                "value_code": obs.value_code,
                "risk_level": obs.risk_level.value if obs.risk_level else None,
                "created_at": datetime.utcnow().isoformat(),
            }
            vertices.append(obs_vertex)
            
            edges.append({
                "label": "HAS_OBSERVATION",
                "from_label": "SDOHScreening",
                "from_id": screening_id,
                "to_label": "SDOHObservation",
                "to_id": obs_id,
                "tenant_id": self.tenant_id,
            })
            
            # If high risk, create a "need" vertex
            if obs.risk_level in (RiskLevel.HIGH, RiskLevel.URGENT):
                need_id = f"SDOHNeed/{screening.patient_id}-{obs.domain.value}"
                
                need_vertex = {
                    "label": "SDOHNeed",
                    "id": need_id,
                    "tenant_id": self.tenant_id,
                    "domain": obs.domain.value,
                    "risk_level": obs.risk_level.value,
                    "identified_date": screening.screening_date.isoformat(),
                    "status": "identified",
                    "created_at": datetime.utcnow().isoformat(),
                }
                vertices.append(need_vertex)
                
                edges.append({
                    "label": "HAS_SDOH_NEED",
                    "from_label": "Patient",
                    "from_id": patient_id,
                    "to_label": "SDOHNeed",
                    "to_id": need_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges


# Sample SDOH screening for testing
SAMPLE_SDOH = {
    "screening_id": "SDOH-001",
    "patient_id": "PAT12345",
    "screening_date": "2024-01-15T10:30:00",
    "screening_tool": "PRAPARE",
    "observations": [
        {
            "domain": "housing_instability",
            "code": "71802-3",
            "display": "Housing status",
            "value": "I have a steady place to live",
            "risk_level": "low",
        },
        {
            "domain": "food_insecurity",
            "code": "88122-7",
            "display": "Food insecurity risk",
            "value": "Often true",
            "risk_level": "high",
        },
        {
            "domain": "transportation_insecurity",
            "code": "93030-5",
            "display": "Transportation needs",
            "value": "Yes, it has kept me from medical appointments",
            "risk_level": "moderate",
        },
    ],
    "overall_risk": "high",
    "referrals_needed": ["Food bank", "Transportation assistance"],
}
