"""Analytics Connector - HEDIS, Risk Scores"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult

logger = structlog.get_logger(__name__)

class MeasureType(str, Enum):
    HEDIS = "hedis"
    QUALITY = "quality"
    STAR = "star"

class RiskModelType(str, Enum):
    HCC = "hcc"
    LACE = "lace"
    HOSPITAL_READMISSION = "hospital-readmission"
    MORTALITY = "mortality"

@dataclass
class QualityMeasure:
    measure_id: str
    measure_name: str
    measure_type: MeasureType
    patient_id: str
    numerator: bool
    denominator: bool
    exclusion: bool
    measurement_period: str
    score: float | None = None

@dataclass
class RiskScore:
    score_id: str
    patient_id: str
    model_type: RiskModelType
    score: float
    percentile: float | None = None
    risk_factors: list[str] = None
    calculated_at: datetime | None = None

class AnalyticsConnector(BaseConnector):
    def __init__(self, tenant_id: str, source_system: str = "analytics"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "analytics"
    
    async def parse(self, data: Any) -> ConnectorResult:
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be dict"])
        try:
            data_type = data.get("type", "")
            if data_type == "hedis" or data_type == "quality":
                return self._parse_measure(data)
            elif data_type == "risk":
                return self._parse_risk(data)
            else:
                return ConnectorResult(success=False, errors=["Unknown type"])
        except Exception as e:
            return ConnectorResult(success=False, errors=[str(e)])
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be dict")
        elif not data.get("patient_id"):
            errors.append("Missing patient_id")
        return errors
    
    def _parse_measure(self, data: dict) -> ConnectorResult:
        measure = QualityMeasure(data.get("measure_id", ""), data.get("measure_name", ""),
            MeasureType(data.get("measure_type", "hedis")), data.get("patient_id", ""),
            data.get("numerator", False), data.get("denominator", True),
            data.get("exclusion", False), data.get("measurement_period", ""),
            data.get("score"))
        vertices, edges = [], []
        mid = f"QualityMeasure/{measure.measure_id}-{measure.patient_id}"
        vertices.append(self._create_vertex("QualityMeasure", mid, {
            "measure_id": measure.measure_id, "measure_name": measure.measure_name,
            "measure_type": measure.measure_type.value, "numerator": measure.numerator,
            "denominator": measure.denominator, "exclusion": measure.exclusion,
            "measurement_period": measure.measurement_period, "score": measure.score}))
        edges.append(self._create_edge("HAS_QUALITY_MEASURE", "Patient",
            f"Patient/{measure.patient_id}", "QualityMeasure", mid))
        return ConnectorResult(success=True, vertices=vertices, edges=edges,
            metadata={"measure_id": measure.measure_id})
    
    def _parse_risk(self, data: dict) -> ConnectorResult:
        calc_at = data.get("calculated_at")
        if isinstance(calc_at, str):
            calc_at = datetime.fromisoformat(calc_at.replace("Z", "+00:00"))
        risk = RiskScore(data.get("score_id", ""), data.get("patient_id", ""),
            RiskModelType(data.get("model_type", "hcc")), data.get("score", 0),
            data.get("percentile"), data.get("risk_factors", []), calc_at)
        vertices, edges = [], []
        rid = f"RiskScore/{risk.score_id}"
        vertices.append(self._create_vertex("RiskScore", rid, {
            "score_id": risk.score_id, "model_type": risk.model_type.value,
            "score": risk.score, "percentile": risk.percentile,
            "risk_factors": risk.risk_factors,
            "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None}))
        edges.append(self._create_edge("HAS_RISK_SCORE", "Patient",
            f"Patient/{risk.patient_id}", "RiskScore", rid))
        return ConnectorResult(success=True, vertices=vertices, edges=edges,
            metadata={"score_id": risk.score_id, "score": risk.score})

SAMPLE_HEDIS = {"type": "hedis", "measure_id": "CDC-HBA1C", "measure_name": "Diabetes HbA1c Control",
    "measure_type": "hedis", "patient_id": "PAT12345", "numerator": True, "denominator": True,
    "exclusion": False, "measurement_period": "2024", "score": 0.85}

SAMPLE_RISK = {"type": "risk", "score_id": "RISK-001", "patient_id": "PAT12345",
    "model_type": "hcc", "score": 1.25, "percentile": 75,
    "risk_factors": ["Diabetes", "CKD Stage 3", "CHF"], "calculated_at": "2024-01-15"}
