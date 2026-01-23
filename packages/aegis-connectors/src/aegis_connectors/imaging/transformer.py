"""
Imaging to Graph Transformer
"""

from datetime import datetime
import structlog

from aegis_connectors.imaging.parser import DICOMStudy

logger = structlog.get_logger(__name__)


class ImagingTransformer:
    """Transforms DICOM metadata to graph vertices/edges."""
    
    def __init__(self, tenant_id: str, source_system: str = "imaging"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def transform(self, study: DICOMStudy) -> tuple[list[dict], list[dict]]:
        """Transform DICOM study to vertices and edges."""
        vertices = []
        edges = []
        
        study_id = f"ImagingStudy/{study.study_instance_uid}"
        
        study_vertex = {
            "label": "ImagingStudy",
            "id": study_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "study_instance_uid": study.study_instance_uid,
            "study_id": study.study_id,
            "study_date": study.study_date,
            "study_description": study.study_description,
            "accession_number": study.accession_number,
            "institution_name": study.institution_name,
            "modalities": study.modalities,
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(study_vertex)
        
        if study.patient_id:
            edges.append({
                "label": "HAS_IMAGING_STUDY",
                "from_label": "Patient",
                "from_id": f"Patient/{study.patient_id}",
                "to_label": "ImagingStudy",
                "to_id": study_id,
                "tenant_id": self.tenant_id,
            })
        
        for series in study.series:
            series_id = f"ImagingSeries/{series.series_instance_uid}"
            
            series_vertex = {
                "label": "ImagingSeries",
                "id": series_id,
                "tenant_id": self.tenant_id,
                "modality": series.modality,
                "series_description": series.series_description,
                "created_at": datetime.utcnow().isoformat(),
            }
            vertices.append(series_vertex)
            
            edges.append({
                "label": "HAS_SERIES",
                "from_label": "ImagingStudy",
                "from_id": study_id,
                "to_label": "ImagingSeries",
                "to_id": series_id,
                "tenant_id": self.tenant_id,
            })
        
        return vertices, edges
