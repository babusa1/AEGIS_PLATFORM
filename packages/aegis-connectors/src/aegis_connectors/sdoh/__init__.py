"""
SDOH Connector

Ingests Social Determinants of Health data:
- Housing status
- Food security
- Transportation
- Education
- Employment
- Social support
"""

from aegis_connectors.sdoh.connector import SDOHConnector
from aegis_connectors.sdoh.domains import SDOHDomain, SDOHScreening

__all__ = ["SDOHConnector", "SDOHDomain", "SDOHScreening"]
