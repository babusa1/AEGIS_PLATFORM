"""
FHIR R4 Integration

Supports:
- Epic FHIR R4
- Cerner FHIR R4
- Generic FHIR R4 servers
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import aiohttp
import json
import base64

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# FHIR Models
# =============================================================================

class FHIRResourceType(str, Enum):
    """FHIR R4 resource types."""
    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    ENCOUNTER = "Encounter"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"
    OBSERVATION = "Observation"
    MEDICATION_REQUEST = "MedicationRequest"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    IMMUNIZATION = "Immunization"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    DOCUMENT_REFERENCE = "DocumentReference"
    CLAIM = "Claim"
    COVERAGE = "Coverage"
    EXPLANATION_OF_BENEFIT = "ExplanationOfBenefit"


class FHIRResource(BaseModel):
    """A FHIR resource."""
    resource_type: str
    id: Optional[str] = None
    meta: Optional[dict] = None
    data: dict = Field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> "FHIRResource":
        """Create from dictionary."""
        return cls(
            resource_type=data.get("resourceType", "Unknown"),
            id=data.get("id"),
            meta=data.get("meta"),
            data=data,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.data


class FHIRBundle(BaseModel):
    """A FHIR Bundle containing multiple resources."""
    bundle_type: str = "searchset"
    total: int = 0
    entries: List[FHIRResource] = Field(default_factory=list)
    next_link: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "FHIRBundle":
        """Create from dictionary."""
        entries = []
        for entry in data.get("entry", []):
            if "resource" in entry:
                entries.append(FHIRResource.from_dict(entry["resource"]))
        
        next_link = None
        for link in data.get("link", []):
            if link.get("relation") == "next":
                next_link = link.get("url")
        
        return cls(
            bundle_type=data.get("type", "searchset"),
            total=data.get("total", len(entries)),
            entries=entries,
            next_link=next_link,
        )


# =============================================================================
# FHIR Client
# =============================================================================

class FHIRClient:
    """
    Generic FHIR R4 client.
    
    Features:
    - CRUD operations
    - Search with parameters
    - Pagination
    - Batch operations
    - OAuth2 authentication
    """
    
    def __init__(
        self,
        base_url: str,
        client_id: str = None,
        client_secret: str = None,
        access_token: str = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._token_expiry: Optional[datetime] = None
        self.timeout = timeout
    
    async def _get_headers(self) -> dict:
        """Get request headers with auth."""
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }
        
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return headers
    
    async def _refresh_token(self):
        """Refresh OAuth2 token."""
        # Override in subclasses for specific auth flows
        pass
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    async def read(
        self,
        resource_type: str,
        resource_id: str,
    ) -> Optional[FHIRResource]:
        """Read a single resource."""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return FHIRResource.from_dict(data)
                    elif response.status == 404:
                        return None
                    else:
                        logger.error(f"FHIR read failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"FHIR read error: {e}")
            return None
    
    async def search(
        self,
        resource_type: str,
        params: Dict[str, Any] = None,
        count: int = 100,
    ) -> FHIRBundle:
        """Search for resources."""
        url = f"{self.base_url}/{resource_type}"
        
        search_params = params or {}
        search_params["_count"] = count
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.get(
                    url,
                    headers=headers,
                    params=search_params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return FHIRBundle.from_dict(data)
                    else:
                        logger.error(f"FHIR search failed: {response.status}")
                        return FHIRBundle()
        except Exception as e:
            logger.error(f"FHIR search error: {e}")
            return FHIRBundle()
    
    async def create(
        self,
        resource: FHIRResource,
    ) -> Optional[FHIRResource]:
        """Create a new resource."""
        url = f"{self.base_url}/{resource.resource_type}"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.post(
                    url,
                    headers=headers,
                    json=resource.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        return FHIRResource.from_dict(data)
                    else:
                        logger.error(f"FHIR create failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"FHIR create error: {e}")
            return None
    
    async def update(
        self,
        resource: FHIRResource,
    ) -> Optional[FHIRResource]:
        """Update an existing resource."""
        if not resource.id:
            raise ValueError("Resource ID required for update")
        
        url = f"{self.base_url}/{resource.resource_type}/{resource.id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.put(
                    url,
                    headers=headers,
                    json=resource.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        return FHIRResource.from_dict(data)
                    else:
                        logger.error(f"FHIR update failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"FHIR update error: {e}")
            return None
    
    async def delete(
        self,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """Delete a resource."""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.delete(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    return response.status in [200, 204]
        except Exception as e:
            logger.error(f"FHIR delete error: {e}")
            return False
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def get_patient(self, patient_id: str) -> Optional[FHIRResource]:
        """Get a patient by ID."""
        return await self.read("Patient", patient_id)
    
    async def search_patients(
        self,
        name: str = None,
        identifier: str = None,
        birthdate: str = None,
        **kwargs,
    ) -> FHIRBundle:
        """Search for patients."""
        params = {}
        if name:
            params["name"] = name
        if identifier:
            params["identifier"] = identifier
        if birthdate:
            params["birthdate"] = birthdate
        params.update(kwargs)
        
        return await self.search("Patient", params)
    
    async def get_patient_everything(
        self,
        patient_id: str,
    ) -> FHIRBundle:
        """Get everything for a patient ($everything operation)."""
        url = f"{self.base_url}/Patient/{patient_id}/$everything"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers()
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return FHIRBundle.from_dict(data)
                    else:
                        return FHIRBundle()
        except Exception as e:
            logger.error(f"FHIR $everything error: {e}")
            return FHIRBundle()
    
    async def get_encounters(
        self,
        patient_id: str = None,
        status: str = None,
    ) -> FHIRBundle:
        """Get encounters."""
        params = {}
        if patient_id:
            params["patient"] = patient_id
        if status:
            params["status"] = status
        return await self.search("Encounter", params)
    
    async def get_conditions(
        self,
        patient_id: str,
        clinical_status: str = "active",
    ) -> FHIRBundle:
        """Get conditions for a patient."""
        params = {
            "patient": patient_id,
        }
        if clinical_status:
            params["clinical-status"] = clinical_status
        return await self.search("Condition", params)
    
    async def get_observations(
        self,
        patient_id: str,
        category: str = None,
        code: str = None,
    ) -> FHIRBundle:
        """Get observations (labs, vitals) for a patient."""
        params = {"patient": patient_id}
        if category:
            params["category"] = category
        if code:
            params["code"] = code
        return await self.search("Observation", params)


# =============================================================================
# Epic FHIR Client
# =============================================================================

class EpicFHIRClient(FHIRClient):
    """
    Epic FHIR R4 client.
    
    Implements Epic-specific:
    - OAuth2 with SMART on FHIR
    - Epic-specific search parameters
    - MyChart integration
    """
    
    EPIC_SANDBOX = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    
    def __init__(
        self,
        base_url: str = None,
        client_id: str = None,
        private_key: str = None,
        **kwargs,
    ):
        super().__init__(
            base_url=base_url or self.EPIC_SANDBOX,
            client_id=client_id,
            **kwargs,
        )
        self.private_key = private_key
        self._token_url = f"{self.base_url.rsplit('/api', 1)[0]}/oauth2/token"
    
    async def _refresh_token(self):
        """
        Refresh Epic OAuth2 token using JWT assertion.
        
        Epic uses Backend Services auth with JWT.
        """
        if not self.client_id or not self.private_key:
            logger.warning("Epic credentials not configured")
            return
        
        # In production, create JWT assertion and exchange for token
        # This is a simplified example
        try:
            import jwt
            from datetime import timedelta
            
            now = datetime.utcnow()
            claims = {
                "iss": self.client_id,
                "sub": self.client_id,
                "aud": self._token_url,
                "jti": str(__import__('uuid').uuid4()),
                "exp": now + timedelta(minutes=5),
                "iat": now,
            }
            
            assertion = jwt.encode(
                claims,
                self.private_key,
                algorithm="RS384",
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                        "client_assertion": assertion,
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data["access_token"]
                        self._token_expiry = now + timedelta(seconds=data.get("expires_in", 3600))
                        logger.info("Epic token refreshed")
                        
        except ImportError:
            logger.warning("PyJWT not installed for Epic auth")
        except Exception as e:
            logger.error(f"Epic token refresh failed: {e}")
    
    async def search_patients_by_mrn(
        self,
        mrn: str,
        system: str = None,
    ) -> FHIRBundle:
        """Search patients by MRN (Epic identifier)."""
        identifier = f"{system}|{mrn}" if system else mrn
        return await self.search_patients(identifier=identifier)
    
    async def get_patient_chart(
        self,
        patient_id: str,
    ) -> dict:
        """Get patient chart summary (Epic-specific)."""
        # Get patient demographics
        patient = await self.get_patient(patient_id)
        
        # Get active conditions
        conditions = await self.get_conditions(patient_id)
        
        # Get recent encounters
        encounters = await self.get_encounters(patient_id)
        
        # Get recent observations
        observations = await self.get_observations(patient_id)
        
        return {
            "patient": patient.data if patient else None,
            "conditions": [c.data for c in conditions.entries],
            "encounters": [e.data for e in encounters.entries[:10]],
            "observations": [o.data for o in observations.entries[:50]],
        }


# =============================================================================
# Cerner FHIR Client
# =============================================================================

class CernerFHIRClient(FHIRClient):
    """
    Cerner FHIR R4 client.
    
    Implements Cerner-specific features.
    """
    
    CERNER_SANDBOX = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    
    def __init__(
        self,
        base_url: str = None,
        **kwargs,
    ):
        super().__init__(
            base_url=base_url or self.CERNER_SANDBOX,
            **kwargs,
        )
