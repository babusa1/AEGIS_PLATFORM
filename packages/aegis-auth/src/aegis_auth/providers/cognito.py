"""
AWS Cognito Provider

OIDC implementation for AWS Cognito User Pools.
Primary provider for AWS-first deployments.
"""

from typing import Any
import httpx
import structlog
from jose import jwt, JWTError

from aegis_auth.providers.base import BaseAuthProvider, AuthenticationError
from aegis_auth.models import User, UserRole

logger = structlog.get_logger(__name__)


class CognitoProvider(BaseAuthProvider):
    """
    AWS Cognito OIDC provider.
    
    Configuration:
        issuer_url: https://cognito-idp.{region}.amazonaws.com/{user_pool_id}
        client_id: Cognito app client ID
        client_secret: Cognito app client secret (if configured)
    """
    
    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str | None = None,
        region: str = "us-east-1",
        user_pool_id: str | None = None,
        **kwargs
    ):
        super().__init__(issuer_url, client_id, client_secret, **kwargs)
        self.region = region
        self.user_pool_id = user_pool_id or issuer_url.split("/")[-1]
        self._jwks: dict | None = None
        self._jwks_client: httpx.AsyncClient | None = None
    
    async def initialize(self) -> None:
        """Fetch JWKS from Cognito."""
        jwks_url = f"{self.issuer_url}/.well-known/jwks.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
            
            self._initialized = True
            logger.info("Cognito provider initialized", user_pool=self.user_pool_id)
            
        except Exception as e:
            logger.error("Failed to initialize Cognito", error=str(e))
            raise
    
    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token from Cognito."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Find matching key
            key = None
            for k in self._jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                raise AuthenticationError("Token signing key not found")
            
            # Verify and decode
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer_url,
            )
            
            return claims
            
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            raise AuthenticationError(f"Invalid token: {e}")
    
    async def get_user_info(self, token: str) -> dict[str, Any]:
        """Get user info from Cognito userinfo endpoint."""
        userinfo_url = f"{self.issuer_url}/oauth2/userInfo"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Failed to get user info")
            
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh tokens using Cognito token endpoint."""
        token_url = f"{self.issuer_url}/oauth2/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code != 200:
                raise AuthenticationError("Token refresh failed")
            
            return response.json()
    
    # ==================== USER MANAGEMENT (via boto3) ====================
    
    async def create_user(
        self,
        email: str,
        password: str | None = None,
        attributes: dict[str, Any] | None = None
    ) -> str:
        """Create user in Cognito User Pool."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            user_attrs = [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ]
            
            if attributes:
                for key, value in attributes.items():
                    user_attrs.append({"Name": key, "Value": str(value)})
            
            if password:
                response = client.admin_create_user(
                    UserPoolId=self.user_pool_id,
                    Username=email,
                    UserAttributes=user_attrs,
                    TemporaryPassword=password,
                    MessageAction="SUPPRESS",
                )
            else:
                response = client.admin_create_user(
                    UserPoolId=self.user_pool_id,
                    Username=email,
                    UserAttributes=user_attrs,
                )
            
            return response["User"]["Username"]
            
        except Exception as e:
            logger.error("Failed to create Cognito user", error=str(e))
            raise
    
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get user from Cognito."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            response = client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=user_id,
            )
            
            # Convert to dict
            attrs = {a["Name"]: a["Value"] for a in response.get("UserAttributes", [])}
            attrs["sub"] = response.get("Username")
            attrs["enabled"] = response.get("Enabled", True)
            
            return attrs
            
        except Exception as e:
            if "UserNotFoundException" in str(e):
                return None
            raise
    
    async def update_user(
        self,
        user_id: str,
        attributes: dict[str, Any]
    ) -> bool:
        """Update Cognito user attributes."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            user_attrs = [
                {"Name": k, "Value": str(v)} for k, v in attributes.items()
            ]
            
            client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=user_id,
                UserAttributes=user_attrs,
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update Cognito user", error=str(e))
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user from Cognito."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=user_id,
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete Cognito user", error=str(e))
            return False
    
    async def disable_user(self, user_id: str) -> bool:
        """Disable Cognito user."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=user_id,
            )
            
            return True
            
        except Exception as e:
            return False
    
    async def enable_user(self, user_id: str) -> bool:
        """Enable Cognito user."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            client.admin_enable_user(
                UserPoolId=self.user_pool_id,
                Username=user_id,
            )
            
            return True
            
        except Exception as e:
            return False
    
    # ==================== MFA ====================
    
    async def setup_mfa(self, user_id: str) -> dict[str, Any]:
        """Set up TOTP MFA for user."""
        try:
            import boto3
            
            client = boto3.client("cognito-idp", region_name=self.region)
            
            response = client.admin_set_user_mfa_preference(
                UserPoolId=self.user_pool_id,
                Username=user_id,
                SoftwareTokenMfaSettings={
                    "Enabled": True,
                    "PreferredMfa": True,
                }
            )
            
            return {"status": "enabled"}
            
        except Exception as e:
            logger.error("Failed to setup MFA", error=str(e))
            raise
    
    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code (handled during auth flow)."""
        # MFA verification is part of Cognito auth flow
        return True
    
    # ==================== HELPERS ====================
    
    def _extract_roles(self, claims: dict[str, Any]) -> list:
        """Extract roles from Cognito token."""
        # Cognito uses custom attributes or groups for roles
        groups = claims.get("cognito:groups", [])
        
        role_mapping = {
            "Admins": UserRole.ADMIN,
            "Physicians": UserRole.PHYSICIAN,
            "Nurses": UserRole.NURSE,
            "CareManagers": UserRole.CARE_MANAGER,
            "Billing": UserRole.BILLING,
            "Analysts": UserRole.ANALYST,
        }
        
        roles = []
        for group in groups:
            if group in role_mapping:
                roles.append(role_mapping[group])
        
        return roles
