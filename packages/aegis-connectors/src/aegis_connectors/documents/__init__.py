"""
Document Connectors

Parses clinical documents:
- CDA/CCDA (structured XML)
- PDF (text extraction)
- NLP (entity extraction from notes)
"""

from aegis_connectors.documents.connector import DocumentConnector
from aegis_connectors.documents.pdf import PDFConnector, PDFExtractor
from aegis_connectors.documents.nlp import NLPConnector, ClinicalNLPExtractor

__all__ = [
    "DocumentConnector",
    "PDFConnector",
    "PDFExtractor",
    "NLPConnector",
    "ClinicalNLPExtractor",
]
