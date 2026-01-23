"""
AEGIS Data Ingestion Module

Parsers and writers for healthcare data standards:
- FHIR R4
- HL7v2
- EDI 837/835

Also includes synthetic data generation for testing.
"""

from aegis.ingestion.fhir_parser import FHIRParser
from aegis.ingestion.graph_writer import GraphWriter
from aegis.ingestion.synthetic_data import SyntheticDataGenerator
from aegis.ingestion.service import IngestionService

__all__ = [
    "FHIRParser",
    "GraphWriter", 
    "SyntheticDataGenerator",
    "IngestionService",
]
