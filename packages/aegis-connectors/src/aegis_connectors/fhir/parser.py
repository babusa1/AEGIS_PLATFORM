"""
FHIR R4 Parser

Parses FHIR R4 resources using the fhir.resources library.
"""

import json
from typing import Any
import structlog

from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.procedure import Procedure
from fhir.resources.claim import Claim
from fhir.resources.coverage import Coverage
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.careplan import CarePlan
from fhir.resources.careteam import CareTeam
from fhir.resources.practitioner import Practitioner
from fhir.resources.organization import Organization
from fhir.resources.location import Location

logger = structlog.get_logger(__name__)

# Map FHIR resource types to their classes
RESOURCE_CLASSES = {
    "Patient": Patient,
    "Encounter": Encounter,
    "Condition": Condition,
    "Observation": Observation,
    "MedicationRequest": MedicationRequest,
    "Procedure": Procedure,
    "Claim": Claim,
    "Coverage": Coverage,
    "DiagnosticReport": DiagnosticReport,
    "CarePlan": CarePlan,
    "CareTeam": CareTeam,
    "Practitioner": Practitioner,
    "Organization": Organization,
    "Location": Location,
}


class FHIRParser:
    """
    Parses FHIR R4 resources.
    
    Supports:
    - Single resources (JSON dict)
    - Bundles (transaction, searchset, etc.)
    - NDJSON (bulk export format)
    """
    
    def parse_bundle(self, data: str | dict) -> tuple[list[Any], list[str]]:
        """
        Parse a FHIR Bundle.
        
        Args:
            data: JSON string or dict
            
        Returns:
            Tuple of (resources, errors)
        """
        errors = []
        resources = []
        
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            bundle = Bundle.model_validate(data)
            
            if bundle.entry:
                for entry in bundle.entry:
                    if entry.resource:
                        resources.append(entry.resource)
            
            logger.info(f"Parsed bundle with {len(resources)} resources")
            
        except Exception as e:
            errors.append(f"Bundle parse error: {str(e)}")
            logger.error("Failed to parse bundle", error=str(e))
        
        return resources, errors
    
    def parse_resource(self, data: str | dict) -> tuple[Any | None, list[str]]:
        """
        Parse a single FHIR resource.
        
        Args:
            data: JSON string or dict
            
        Returns:
            Tuple of (resource, errors)
        """
        errors = []
        
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            resource_type = data.get("resourceType")
            
            if not resource_type:
                errors.append("Missing resourceType")
                return None, errors
            
            resource_class = RESOURCE_CLASSES.get(resource_type)
            
            if resource_class:
                resource = resource_class.model_validate(data)
                return resource, errors
            else:
                # Unknown resource type - return raw dict
                logger.warning(f"Unknown resource type: {resource_type}")
                return data, errors
                
        except Exception as e:
            errors.append(f"Resource parse error: {str(e)}")
            logger.error("Failed to parse resource", error=str(e))
            return None, errors
    
    def parse_ndjson(self, data: str) -> tuple[list[Any], list[str]]:
        """
        Parse NDJSON (newline-delimited JSON) format.
        
        Used by FHIR Bulk Data export.
        """
        resources = []
        errors = []
        
        for line_num, line in enumerate(data.strip().split("\n"), 1):
            if not line.strip():
                continue
            
            resource, line_errors = self.parse_resource(line)
            
            if resource:
                resources.append(resource)
            
            for err in line_errors:
                errors.append(f"Line {line_num}: {err}")
        
        return resources, errors
    
    def validate_resource(self, data: str | dict) -> list[str]:
        """Validate a FHIR resource without parsing."""
        errors = []
        
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            resource_type = data.get("resourceType")
            
            if not resource_type:
                errors.append("Missing resourceType")
                return errors
            
            resource_class = RESOURCE_CLASSES.get(resource_type)
            
            if resource_class:
                # Pydantic validation
                resource_class.model_validate(data)
            
        except Exception as e:
            errors.append(str(e))
        
        return errors
