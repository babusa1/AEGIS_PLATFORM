"""DICOMweb Client - QIDO/WADO/STOW"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class DICOMwebStudy:
    study_instance_uid: str
    patient_id: str | None = None
    patient_name: str | None = None
    study_date: str | None = None
    study_description: str | None = None
    modalities: list[str] = field(default_factory=list)
    num_series: int = 0
    num_instances: int = 0

class DICOMwebClient:
    """DICOMweb client supporting QIDO-RS, WADO-RS, STOW-RS."""
    
    def __init__(self, base_url: str, auth_token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
    
    async def qido_search_studies(self, patient_id: str | None = None,
            study_date: str | None = None, modality: str | None = None) -> list[DICOMwebStudy]:
        """QIDO-RS: Search for studies. Returns stub without real endpoint."""
        logger.info("QIDO search_studies", patient_id=patient_id, study_date=study_date)
        return []
    
    async def wado_retrieve_study(self, study_uid: str) -> bytes | None:
        """WADO-RS: Retrieve study. Returns None without real endpoint."""
        logger.info("WADO retrieve_study", study_uid=study_uid)
        return None
    
    async def stow_store(self, dicom_data: bytes) -> dict:
        """STOW-RS: Store DICOM instance. Returns stub without real endpoint."""
        logger.info("STOW store", size=len(dicom_data))
        return {"status": "stub"}
    
    def parse_qido_response(self, data: list[dict]) -> list[DICOMwebStudy]:
        studies = []
        for entry in data:
            studies.append(DICOMwebStudy(
                study_instance_uid=self._get_value(entry, "0020000D"),
                patient_id=self._get_value(entry, "00100020"),
                patient_name=self._get_value(entry, "00100010"),
                study_date=self._get_value(entry, "00080020"),
                study_description=self._get_value(entry, "00081030"),
                modalities=self._get_values(entry, "00080061"),
                num_series=int(self._get_value(entry, "00201206") or 0),
                num_instances=int(self._get_value(entry, "00201208") or 0)))
        return studies
    
    def _get_value(self, entry: dict, tag: str) -> str | None:
        val = entry.get(tag, {})
        if isinstance(val, dict) and "Value" in val:
            return str(val["Value"][0]) if val["Value"] else None
        return None
    
    def _get_values(self, entry: dict, tag: str) -> list[str]:
        val = entry.get(tag, {})
        if isinstance(val, dict) and "Value" in val:
            return [str(v) for v in val["Value"]]
        return []

class DICOMwebConnector:
    """DICOMweb Connector."""
    
    def __init__(self, tenant_id: str, base_url: str = "http://localhost:8080/dicomweb"):
        self.tenant_id = tenant_id
        self.client = DICOMwebClient(base_url)
    
    def transform_studies(self, studies: list[DICOMwebStudy]):
        vertices, edges = [], []
        for s in studies:
            sid = f"ImagingStudy/{s.study_instance_uid}"
            vertices.append({"label": "ImagingStudy", "id": sid, "tenant_id": self.tenant_id,
                "study_instance_uid": s.study_instance_uid, "study_date": s.study_date,
                "study_description": s.study_description, "modalities": s.modalities,
                "num_series": s.num_series, "num_instances": s.num_instances,
                "created_at": datetime.utcnow().isoformat()})
            if s.patient_id:
                edges.append({"label": "HAS_IMAGING_STUDY", "from_label": "Patient",
                    "from_id": f"Patient/{s.patient_id}", "to_label": "ImagingStudy",
                    "to_id": sid, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_QIDO = [{"0020000D": {"Value": ["1.2.3.4.5"]}, "00100020": {"Value": ["PAT12345"]},
    "00080020": {"Value": ["20240115"]}, "00081030": {"Value": ["CT Chest"]},
    "00080061": {"Value": ["CT"]}, "00201206": {"Value": [3]}, "00201208": {"Value": [150]}}]
