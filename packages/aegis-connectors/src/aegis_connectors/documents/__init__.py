"""
Document Connector

Parses clinical documents:
- CDA (Clinical Document Architecture)
- C-CDA (Consolidated CDA)
- PDF with extracted text
"""

from aegis_connectors.documents.parser import DocumentParser
from aegis_connectors.documents.connector import DocumentConnector

__all__ = ["DocumentParser", "DocumentConnector"]
