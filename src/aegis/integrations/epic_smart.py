"""
Epic SMART-on-FHIR Integration

Complete OAuth 2.0 flow for Epic EHR integration:
- Authorization code flow with PKCE
- Token management (access + refresh)
- FHIR resource access
- Bulk data export ($export)
- Epic sandbox support
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import base64
import hashlib
import secrets
import json
import asyncio

import structlog
from pydantic import BaseModel, Field
import httpx

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class EpicEnvironment(str, Enum):
    """Epic environment types."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EpicConfig(BaseModel):
    """Epic SMART-on-FHIR configuration."""
    environment: EpicEnvironment = EpicEnvironment.SANDBOX
    
    # App registration
    client_id: str
    client_secret: Optional[str] = None  # For confidential apps
    
    # Endpoints (auto-populated based on environment)
    authorize_url: str = ""
    token_url: str = ""
    fhir_base_url: str = ""
    
    # Redirect
    redirect_uri: str = "http://localhost:8000/v1/integrations/epic/callback"
    
    # Scopes
    scopes: List[str] = Field(default_factory=lambda: [
        "launch",
        "openid",
        "fhirUser",
        "patient/*.read",
        "user/*.read",
    ])
    
    def __init__(self, **data):
        super().__init__(**data)
        self._set_endpoints()
    
    def _set_endpoints(self):
        """Set endpoints based on environment."""
        if self.environment == EpicEnvironment.SANDBOX:
            self.authorize_url = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
            self.token_url = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
            self.fhir_base_url = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
        else:
            # Production would be customer-specific
            pass


# Epic sandbox test credentials
EPIC_SANDBOX_CONFIG = EpicConfig(
    environment=EpicEnvironment.SANDBOX,
    client_id="your-registered-client-id",  # Register at https://fhir.epic.com/
    redirect_uri="http://localhost:8000/v1/integrations/epic/callback",
    scopes=[
        "launch",
        "openid", 
        "fhirUser",
        "patient/*.read",
        "user/*.read",
        "Observation.read",
        "Condition.read",
        "MedicationRequest.read",
    ],
)


# =============================================================================
# Token Management
# =============================================================================

class TokenSet(BaseModel):
    """OAuth token set."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str = ""
    patient: Optional[str] = None  # Patient context from launch
    id_token: Optional[str] = None
    
    # Calculated
    expires_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.expires_at = datetime.utcnow() + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 5-minute buffer)."""
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))


class TokenStore:
    """
    In-memory token store.
    
    In production, use Redis or database storage.
    """
    
    def __init__(self):
        self._tokens: Dict[str, TokenSet] = {}
        self._states: Dict[str, dict] = {}  # For PKCE and state validation
    
    async def store_token(self, user_id: str, tokens: TokenSet):
        """Store tokens for a user."""
        self._tokens[user_id] = tokens
        logger.info(f"Stored tokens for user {user_id}")
    
    async def get_token(self, user_id: str) -> Optional[TokenSet]:
        """Get tokens for a user."""
        return self._tokens.get(user_id)
    
    async def delete_token(self, user_id: str):
        """Delete tokens for a user."""
        self._tokens.pop(user_id, None)
    
    async def store_state(self, state: str, data: dict):
        """Store OAuth state for validation."""
        self._states[state] = {
            **data,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    async def get_state(self, state: str) -> Optional[dict]:
        """Get and validate OAuth state."""
        return self._states.pop(state, None)


# Global token store
_token_store = TokenStore()


def get_token_store() -> TokenStore:
    """Get global token store."""
    return _token_store


# =============================================================================
# PKCE Support
# =============================================================================

def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.
    
    PKCE (Proof Key for Code Exchange) is required for public clients
    and recommended for confidential clients.
    """
    # Generate code verifier (43-128 chars, URL-safe)
    code_verifier = secrets.token_urlsafe(64)
    
    # Generate code challenge (SHA256 hash, base64url encoded)
    code_challenge_digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).decode().rstrip("=")
    
    return code_verifier, code_challenge


# =============================================================================
# Epic SMART Client
# =============================================================================

class EpicSMARTClient:
    """
    Epic SMART-on-FHIR client.
    
    Handles:
    - Authorization code flow with PKCE
    - Token management
    - FHIR resource access
    - Bulk data export
    """
    
    def __init__(
        self,
        config: EpicConfig = None,
        token_store: TokenStore = None,
    ):
        self.config = config or EPIC_SANDBOX_CONFIG
        self.token_store = token_store or get_token_store()
    
    # =========================================================================
    # Authorization Flow
    # =========================================================================
    
    async def get_authorization_url(
        self,
        user_id: str,
        launch_token: str = None,
        aud: str = None,
    ) -> Tuple[str, str]:
        """
        Generate authorization URL for OAuth flow.
        
        Args:
            user_id: User identifier
            launch_token: EHR launch token (for EHR launch)
            aud: FHIR server URL (audience)
            
        Returns:
            Tuple of (authorization_url, state)
        """
        # Generate PKCE
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Generate state
        state = secrets.token_urlsafe(32)
        
        # Store state for validation
        await self.token_store.store_state(state, {
            "user_id": user_id,
            "code_verifier": code_verifier,
        })
        
        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "aud": aud or self.config.fhir_base_url,
        }
        
        if launch_token:
            params["launch"] = launch_token
        
        # Build URL
        query = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.config.authorize_url}?{query}"
        
        logger.info(f"Generated auth URL for user {user_id}")
        return auth_url, state
    
    async def handle_callback(
        self,
        code: str,
        state: str,
    ) -> TokenSet:
        """
        Handle OAuth callback and exchange code for tokens.
        
        Args:
            code: Authorization code from Epic
            state: State parameter for validation
            
        Returns:
            TokenSet with access and refresh tokens
        """
        # Validate state
        state_data = await self.token_store.get_state(state)
        if not state_data:
            raise ValueError("Invalid or expired state")
        
        user_id = state_data["user_id"]
        code_verifier = state_data["code_verifier"]
        
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "client_id": self.config.client_id,
                    "code_verifier": code_verifier,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")
            
            token_data = response.json()
        
        # Create token set
        tokens = TokenSet(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope", ""),
            patient=token_data.get("patient"),
            id_token=token_data.get("id_token"),
        )
        
        # Store tokens
        await self.token_store.store_token(user_id, tokens)
        
        logger.info(f"Token exchange successful for user {user_id}")
        return tokens
    
    async def refresh_token(self, user_id: str) -> TokenSet:
        """
        Refresh access token using refresh token.
        
        Args:
            user_id: User identifier
            
        Returns:
            New TokenSet
        """
        tokens = await self.token_store.get_token(user_id)
        if not tokens or not tokens.refresh_token:
            raise ValueError("No refresh token available")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": tokens.refresh_token,
                    "client_id": self.config.client_id,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise ValueError("Token refresh failed")
            
            token_data = response.json()
        
        # Create new token set
        new_tokens = TokenSet(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", tokens.refresh_token),
            scope=token_data.get("scope", tokens.scope),
            patient=token_data.get("patient", tokens.patient),
        )
        
        # Store new tokens
        await self.token_store.store_token(user_id, new_tokens)
        
        logger.info(f"Token refreshed for user {user_id}")
        return new_tokens
    
    async def get_valid_token(self, user_id: str) -> str:
        """
        Get valid access token, refreshing if needed.
        
        Args:
            user_id: User identifier
            
        Returns:
            Valid access token
        """
        tokens = await self.token_store.get_token(user_id)
        if not tokens:
            raise ValueError("No tokens found - authorization required")
        
        if tokens.is_expired:
            tokens = await self.refresh_token(user_id)
        
        return tokens.access_token
    
    # =========================================================================
    # FHIR Resource Access
    # =========================================================================
    
    async def get_patient(
        self,
        user_id: str,
        patient_id: str = None,
    ) -> dict:
        """
        Get patient resource.
        
        Args:
            user_id: User identifier
            patient_id: Patient ID (uses launch context if not provided)
            
        Returns:
            FHIR Patient resource
        """
        tokens = await self.token_store.get_token(user_id)
        if not tokens:
            raise ValueError("Authorization required")
        
        patient_id = patient_id or tokens.patient
        if not patient_id:
            raise ValueError("No patient context")
        
        return await self._fhir_request(user_id, f"Patient/{patient_id}")
    
    async def get_conditions(
        self,
        user_id: str,
        patient_id: str,
    ) -> List[dict]:
        """Get patient conditions."""
        result = await self._fhir_request(
            user_id,
            f"Condition?patient={patient_id}&clinical-status=active"
        )
        return result.get("entry", [])
    
    async def get_medications(
        self,
        user_id: str,
        patient_id: str,
    ) -> List[dict]:
        """Get patient medications."""
        result = await self._fhir_request(
            user_id,
            f"MedicationRequest?patient={patient_id}&status=active"
        )
        return result.get("entry", [])
    
    async def get_observations(
        self,
        user_id: str,
        patient_id: str,
        category: str = None,
    ) -> List[dict]:
        """Get patient observations (vitals, labs)."""
        url = f"Observation?patient={patient_id}"
        if category:
            url += f"&category={category}"
        
        result = await self._fhir_request(user_id, url)
        return result.get("entry", [])
    
    async def get_encounters(
        self,
        user_id: str,
        patient_id: str,
    ) -> List[dict]:
        """Get patient encounters."""
        result = await self._fhir_request(
            user_id,
            f"Encounter?patient={patient_id}"
        )
        return result.get("entry", [])
    
    async def get_patient_everything(
        self,
        user_id: str,
        patient_id: str,
    ) -> dict:
        """
        Get all patient data using $everything operation.
        
        Note: May be limited by Epic configuration.
        """
        return await self._fhir_request(
            user_id,
            f"Patient/{patient_id}/$everything"
        )
    
    async def search(
        self,
        user_id: str,
        resource_type: str,
        params: dict,
    ) -> dict:
        """
        Search for FHIR resources.
        
        Args:
            user_id: User identifier
            resource_type: FHIR resource type
            params: Search parameters
            
        Returns:
            FHIR Bundle with search results
        """
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return await self._fhir_request(user_id, f"{resource_type}?{query}")
    
    async def _fhir_request(
        self,
        user_id: str,
        path: str,
        method: str = "GET",
        data: dict = None,
    ) -> dict:
        """Make authenticated FHIR request."""
        token = await self.get_valid_token(user_id)
        
        url = f"{self.config.fhir_base_url}/{path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                },
                json=data,
            )
            
            if response.status_code == 401:
                # Try to refresh and retry
                await self.refresh_token(user_id)
                token = await self.get_valid_token(user_id)
                
                response = await client.request(
                    method=method,
                    url=url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/fhir+json",
                    },
                    json=data,
                )
            
            if response.status_code >= 400:
                logger.error(f"FHIR request failed: {response.status_code} - {response.text}")
                raise ValueError(f"FHIR request failed: {response.status_code}")
            
            return response.json()
    
    # =========================================================================
    # Bulk Data Export
    # =========================================================================
    
    async def initiate_bulk_export(
        self,
        user_id: str,
        resource_types: List[str] = None,
        since: datetime = None,
    ) -> str:
        """
        Initiate bulk data export ($export operation).
        
        Args:
            user_id: User identifier
            resource_types: List of resource types to export
            since: Export data modified after this date
            
        Returns:
            Content-Location URL for status polling
        """
        token = await self.get_valid_token(user_id)
        
        params = {}
        if resource_types:
            params["_type"] = ",".join(resource_types)
        if since:
            params["_since"] = since.isoformat()
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.config.fhir_base_url}/Patient/$export"
        if query:
            url += f"?{query}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                    "Prefer": "respond-async",
                },
            )
            
            if response.status_code != 202:
                raise ValueError(f"Bulk export initiation failed: {response.status_code}")
            
            # Get status URL from Content-Location header
            status_url = response.headers.get("Content-Location")
            if not status_url:
                raise ValueError("No Content-Location header in response")
            
            logger.info(f"Bulk export initiated: {status_url}")
            return status_url
    
    async def check_bulk_export_status(
        self,
        user_id: str,
        status_url: str,
    ) -> dict:
        """
        Check bulk export status.
        
        Returns:
        - {"status": "in-progress"} while processing
        - {"status": "complete", "output": [...]} when done
        - {"status": "error", "error": "..."} on failure
        """
        token = await self.get_valid_token(user_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                status_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                },
            )
            
            if response.status_code == 202:
                # Still processing
                progress = response.headers.get("X-Progress", "unknown")
                return {"status": "in-progress", "progress": progress}
            
            elif response.status_code == 200:
                # Complete
                data = response.json()
                return {
                    "status": "complete",
                    "output": data.get("output", []),
                    "request": data.get("request"),
                    "transactionTime": data.get("transactionTime"),
                }
            
            else:
                return {"status": "error", "error": response.text}
    
    async def download_bulk_export_file(
        self,
        user_id: str,
        file_url: str,
    ) -> List[dict]:
        """
        Download bulk export file (NDJSON format).
        
        Args:
            user_id: User identifier
            file_url: File URL from export status response
            
        Returns:
            List of FHIR resources
        """
        token = await self.get_valid_token(user_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                file_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+ndjson",
                },
            )
            
            if response.status_code != 200:
                raise ValueError(f"Download failed: {response.status_code}")
            
            # Parse NDJSON
            resources = []
            for line in response.text.strip().split("\n"):
                if line:
                    resources.append(json.loads(line))
            
            return resources


# =============================================================================
# API Router
# =============================================================================

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/integrations/epic", tags=["Epic SMART-on-FHIR"])


@router.get("/authorize")
async def initiate_authorization(
    user_id: str = Query(..., description="User identifier"),
    launch: str = Query(default=None, description="EHR launch token"),
):
    """
    Initiate Epic SMART-on-FHIR authorization.
    
    Redirects user to Epic authorization page.
    """
    client = EpicSMARTClient()
    auth_url, state = await client.get_authorization_url(
        user_id=user_id,
        launch_token=launch,
    )
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def handle_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
):
    """
    Handle OAuth callback from Epic.
    
    Exchanges authorization code for tokens.
    """
    try:
        client = EpicSMARTClient()
        tokens = await client.handle_callback(code=code, state=state)
        
        return {
            "status": "authorized",
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "scope": tokens.scope,
            "patient_context": tokens.patient,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patient/{patient_id}")
async def get_patient(
    patient_id: str,
    user_id: str = Query(..., description="User identifier"),
):
    """Get patient from Epic."""
    try:
        client = EpicSMARTClient()
        patient = await client.get_patient(user_id, patient_id)
        return patient
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patient/{patient_id}/conditions")
async def get_patient_conditions(
    patient_id: str,
    user_id: str = Query(..., description="User identifier"),
):
    """Get patient conditions from Epic."""
    try:
        client = EpicSMARTClient()
        conditions = await client.get_conditions(user_id, patient_id)
        return {"conditions": conditions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patient/{patient_id}/medications")
async def get_patient_medications(
    patient_id: str,
    user_id: str = Query(..., description="User identifier"),
):
    """Get patient medications from Epic."""
    try:
        client = EpicSMARTClient()
        medications = await client.get_medications(user_id, patient_id)
        return {"medications": medications}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patient/{patient_id}/observations")
async def get_patient_observations(
    patient_id: str,
    user_id: str = Query(..., description="User identifier"),
    category: str = Query(default=None, description="Observation category"),
):
    """Get patient observations (vitals, labs) from Epic."""
    try:
        client = EpicSMARTClient()
        observations = await client.get_observations(user_id, patient_id, category)
        return {"observations": observations}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-export")
async def initiate_bulk_export(
    user_id: str = Query(..., description="User identifier"),
    resource_types: str = Query(default=None, description="Comma-separated resource types"),
):
    """
    Initiate bulk data export from Epic.
    
    Returns status URL for polling.
    """
    try:
        client = EpicSMARTClient()
        types = resource_types.split(",") if resource_types else None
        status_url = await client.initiate_bulk_export(user_id, types)
        return {"status_url": status_url, "status": "initiated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bulk-export/status")
async def check_export_status(
    status_url: str = Query(..., description="Status URL from export initiation"),
    user_id: str = Query(..., description="User identifier"),
):
    """Check bulk export status."""
    try:
        client = EpicSMARTClient()
        status = await client.check_bulk_export_status(user_id, status_url)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connection-status")
async def get_connection_status(
    user_id: str = Query(..., description="User identifier"),
):
    """Check Epic connection status for a user."""
    store = get_token_store()
    tokens = await store.get_token(user_id)
    
    if not tokens:
        return {
            "connected": False,
            "status": "not_authorized",
            "message": "User has not authorized Epic connection",
        }
    
    if tokens.is_expired:
        return {
            "connected": True,
            "status": "token_expired",
            "message": "Token expired, refresh required",
            "patient_context": tokens.patient,
        }
    
    return {
        "connected": True,
        "status": "active",
        "token_type": tokens.token_type,
        "expires_at": tokens.expires_at.isoformat(),
        "patient_context": tokens.patient,
        "scope": tokens.scope,
    }
