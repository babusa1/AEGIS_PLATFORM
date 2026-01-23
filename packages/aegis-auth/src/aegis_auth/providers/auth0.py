"""
Auth0 Provider

OIDC implementation for Auth0.
Alternative provider for non-AWS deployments.
"""

from typing import Any
import httpx
import structlog
from jose import jwt, JWTError

from aegis_auth.providers.base import BaseAuthProvider, AuthenticationError
from aegis_auth.models import UserRole

logger = structlog.get_logger(__name__)


class Auth0Provider(BaseAuthProvider):
    """
    Auth0 OIDC provider.
    
    Configuration:
        issuer_url: https://{domain}.auth0.com
        client_id: Auth0 application client ID
        client_secret: Auth0 application client secret
        audience: API identifier (for access tokens)
    """
    
    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str | None = None,
        audience: str | None = None,
        management_token: str | None = None,
        **kwargs
    ):
        super().__init__(issuer_url, client_id, client_secret, **kwargs)
        self.audience = audience
        self.management_token = management_token
        self.domain = issuer_url.replace("https://", "").rstrip("/")
        self._jwks: dict | None = None
    
    async def initialize(self) -> None:
        """Fetch JWKS from Auth0."""
        jwks_url = f"{self.issuer_url}/.well-known/jwks.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
            
            self._initialized = True
            logger.info("Auth0 provider initialized", domain=self.domain)
            
        except Exception as e:
            logger.error("Failed to initialize Auth0", error=str(e))
            raise
    
    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token from Auth0."""
        if not self._initialized:
            await self.initialize()
        
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            key = None
            for k in self._jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                raise AuthenticationError("Token signing key not found")
            
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience or self.client_id,
                issuer=self.issuer_url + "/",
            )
            
            return claims
            
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            raise AuthenticationError(f"Invalid token: {e}")
    
    async def get_user_info(self, token: str) -> dict[str, Any]:
        """Get user info from Auth0."""
        userinfo_url = f"{self.issuer_url}/userinfo"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Failed to get user info")
            
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh tokens using Auth0."""
        token_url = f"{self.issuer_url}/oauth/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, json=data)
            
            if response.status_code != 200:
                raise AuthenticationError("Token refresh failed")
            
            return response.json()
    
    # ==================== USER MANAGEMENT (via Management API) ====================
    
    async def _get_management_token(self) -> str:
        """Get or refresh management API token."""
        if self.management_token:
            return self.management_token
        
        # Get token from Auth0
        token_url = f"{self.issuer_url}/oauth/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": f"{self.issuer_url}/api/v2/",
                }
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Failed to get management token")
            
            self.management_token = response.json()["access_token"]
            return self.management_token
    
    async def create_user(
        self,
        email: str,
        password: str | None = None,
        attributes: dict[str, Any] | None = None
    ) -> str:
        """Create user via Auth0 Management API."""
        token = await self._get_management_token()
        
        user_data = {
            "email": email,
            "email_verified": True,
            "connection": "Username-Password-Authentication",
        }
        
        if password:
            user_data["password"] = password
        
        if attributes:
            user_data["user_metadata"] = attributes
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.issuer_url}/api/v2/users",
                json=user_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code not in (200, 201):
                raise Exception(f"Failed to create user: {response.text}")
            
            return response.json()["user_id"]
    
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get user from Auth0."""
        token = await self._get_management_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.issuer_url}/api/v2/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 404:
                return None
            
            return response.json()
    
    async def update_user(
        self,
        user_id: str,
        attributes: dict[str, Any]
    ) -> bool:
        """Update Auth0 user."""
        token = await self._get_management_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.issuer_url}/api/v2/users/{user_id}",
                json=attributes,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return response.status_code == 200
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete Auth0 user."""
        token = await self._get_management_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.issuer_url}/api/v2/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return response.status_code == 204
    
    async def disable_user(self, user_id: str) -> bool:
        """Block Auth0 user."""
        return await self.update_user(user_id, {"blocked": True})
    
    async def enable_user(self, user_id: str) -> bool:
        """Unblock Auth0 user."""
        return await self.update_user(user_id, {"blocked": False})
    
    # ==================== MFA ====================
    
    async def setup_mfa(self, user_id: str) -> dict[str, Any]:
        """Set up MFA via Auth0."""
        token = await self._get_management_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.issuer_url}/api/v2/guardian/enrollments/ticket",
                json={"user_id": user_id},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return response.json()
    
    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """MFA verification is handled in Auth0 auth flow."""
        return True
    
    # ==================== HELPERS ====================
    
    def _extract_roles(self, claims: dict[str, Any]) -> list:
        """Extract roles from Auth0 token."""
        # Auth0 can use custom claims or app_metadata
        namespace = "https://aegis.health/"
        roles_claim = claims.get(f"{namespace}roles", [])
        
        if not roles_claim:
            roles_claim = claims.get("roles", [])
        
        role_mapping = {
            "admin": UserRole.ADMIN,
            "physician": UserRole.PHYSICIAN,
            "nurse": UserRole.NURSE,
            "care_manager": UserRole.CARE_MANAGER,
            "billing": UserRole.BILLING,
            "analyst": UserRole.ANALYST,
        }
        
        roles = []
        for role in roles_claim:
            if role.lower() in role_mapping:
                roles.append(role_mapping[role.lower()])
        
        return roles
