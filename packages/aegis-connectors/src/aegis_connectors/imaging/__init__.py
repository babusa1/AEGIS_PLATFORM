"""
Imaging Connectors

Parses medical imaging metadata:
- DICOM (metadata, not pixels)
- DICOMweb (QIDO/WADO/STOW)
"""

from aegis_connectors.imaging.connector import ImagingConnector
from aegis_connectors.imaging.dicomweb import DICOMwebConnector, DICOMwebClient

__all__ = [
    "ImagingConnector",
    "DICOMwebConnector",
    "DICOMwebClient",
]
