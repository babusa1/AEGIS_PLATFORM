"""PDF Text Extraction"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class PDFMetadata:
    title: str | None = None
    author: str | None = None
    page_count: int = 0

@dataclass
class PDFDocument:
    document_id: str
    filename: str
    text: str
    metadata: PDFMetadata
    pages: list[str] = field(default_factory=list)

class PDFExtractor:
    def extract_from_dict(self, data: dict) -> PDFDocument | None:
        try:
            return PDFDocument(
                data.get("document_id", f"PDF-{uuid4().hex[:8]}"),
                data.get("filename", "document.pdf"),
                data.get("text", ""),
                PDFMetadata(data.get("title"), data.get("author"), data.get("page_count", 1)),
                data.get("pages", []))
        except Exception as e:
            logger.error("PDF extraction failed", error=str(e))
            return None

class PDFConnector:
    def __init__(self, tenant_id: str, source_system: str = "pdf"):
        self.tenant_id = tenant_id
        self.source_system = source_system
        self.extractor = PDFExtractor()
    
    def transform(self, doc: PDFDocument, patient_id: str | None = None):
        vertices, edges = [], []
        doc_id = f"DocumentReference/{doc.document_id}"
        vertices.append({"label": "DocumentReference", "id": doc_id, "tenant_id": self.tenant_id,
            "filename": doc.filename, "content_type": "application/pdf", "title": doc.metadata.title,
            "page_count": doc.metadata.page_count, "created_at": datetime.utcnow().isoformat()})
        if patient_id:
            edges.append({"label": "HAS_DOCUMENT", "from_label": "Patient",
                "from_id": f"Patient/{patient_id}", "to_label": "DocumentReference",
                "to_id": doc_id, "tenant_id": self.tenant_id})
        return vertices, edges

SAMPLE_PDF = {"document_id": "PDF-001", "filename": "discharge.pdf", "text": "Discharge summary"}
