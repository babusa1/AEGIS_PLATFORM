"""
Document Connector
"""

from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.documents.parser import DocumentParser, ClinicalDocument

logger = structlog.get_logger(__name__)


class DocumentConnector(BaseConnector):
    """
    Clinical Document Connector.
    
    Parses CDA/C-CDA documents and transforms to graph.
    
    Usage:
        connector = DocumentConnector(tenant_id="hospital-a")
        result = await connector.parse(cda_xml)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "documents"):
        super().__init__(tenant_id, source_system)
        self.parser = DocumentParser()
    
    @property
    def connector_type(self) -> str:
        return "documents"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse clinical document."""
        errors = []
        
        if not isinstance(data, str):
            return ConnectorResult(success=False, errors=["Data must be XML string"])
        
        parsed, parse_errors = self.parser.parse_cda(data)
        errors.extend(parse_errors)
        
        if not parsed:
            return ConnectorResult(success=False, errors=errors)
        
        try:
            vertices, edges = self._transform(parsed)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "Document parse complete",
            type=parsed.document_type,
            vertices=len(vertices),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "document_id": parsed.document_id,
                "document_type": parsed.document_type,
                "patient_id": parsed.patient_id,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        if not isinstance(data, str):
            return ["Data must be XML string"]
        return self.parser.validate(data)
    
    def _transform(self, doc: ClinicalDocument) -> tuple[list[dict], list[dict]]:
        """Transform document to vertices/edges."""
        vertices = []
        edges = []
        
        # Document vertex
        doc_id = f"ClinicalDocument/{doc.document_id}"
        
        doc_vertex = {
            "label": "ClinicalDocument",
            "id": doc_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "document_id": doc.document_id,
            "document_type": doc.document_type,
            "title": doc.title,
            "effective_date": doc.effective_date,
            "author_name": doc.author_name,
            "custodian": doc.custodian,
            "section_count": len(doc.sections),
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(doc_vertex)
        
        # Link to patient
        if doc.patient_id:
            edges.append({
                "label": "HAS_DOCUMENT",
                "from_label": "Patient",
                "from_id": f"Patient/{doc.patient_id}",
                "to_label": "ClinicalDocument",
                "to_id": doc_id,
                "tenant_id": self.tenant_id,
            })
        
        # Extract problems as Conditions
        for i, problem in enumerate(doc.problems):
            if problem.get("code"):
                cond_id = f"Condition/{doc.document_id}-{i}"
                cond_vertex = {
                    "label": "Condition",
                    "id": cond_id,
                    "tenant_id": self.tenant_id,
                    "code": problem.get("code"),
                    "display": problem.get("display"),
                    "code_system": problem.get("code_system"),
                    "source_document": doc_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                vertices.append(cond_vertex)
                
                edges.append({
                    "label": "DOCUMENTS_CONDITION",
                    "from_label": "ClinicalDocument",
                    "from_id": doc_id,
                    "to_label": "Condition",
                    "to_id": cond_id,
                    "tenant_id": self.tenant_id,
                })
        
        # Extract medications
        for i, med in enumerate(doc.medications):
            if med.get("code"):
                med_id = f"Medication/{doc.document_id}-{i}"
                med_vertex = {
                    "label": "Medication",
                    "id": med_id,
                    "tenant_id": self.tenant_id,
                    "code": med.get("code"),
                    "display": med.get("display"),
                    "source_document": doc_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                vertices.append(med_vertex)
                
                edges.append({
                    "label": "DOCUMENTS_MEDICATION",
                    "from_label": "ClinicalDocument",
                    "from_id": doc_id,
                    "to_label": "Medication",
                    "to_id": med_id,
                    "tenant_id": self.tenant_id,
                })
        
        # Extract allergies
        for i, allergy in enumerate(doc.allergies):
            if allergy.get("code") or allergy.get("display"):
                allergy_id = f"Allergy/{doc.document_id}-{i}"
                allergy_vertex = {
                    "label": "AllergyIntolerance",
                    "id": allergy_id,
                    "tenant_id": self.tenant_id,
                    "code": allergy.get("code"),
                    "display": allergy.get("display"),
                    "source_document": doc_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                vertices.append(allergy_vertex)
                
                edges.append({
                    "label": "DOCUMENTS_ALLERGY",
                    "from_label": "ClinicalDocument",
                    "from_id": doc_id,
                    "to_label": "AllergyIntolerance",
                    "to_id": allergy_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges
