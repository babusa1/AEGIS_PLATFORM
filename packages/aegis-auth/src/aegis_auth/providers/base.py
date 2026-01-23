"""
Base Auth Provider

Abstract interface for OIDC authentication providers.
Supports Cognito, Auth0, Okta, and custom OIDC providers.
"""

from abc import ABC, abstractmethod
from typing import Any

import structlog

from aegis_auth.models import User, Tenant

logger = structlog.get_logger(__name__)


class BaseAuthProvider(ABC):
    """
    Abstract base for OIDC authentication providers.
    
    All auth implementations (Cognito, Auth0, Okta) must implement this interface.
    """
    
    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str | None = None,
        **kwargs
    ):
        self.issuer_url = issuer_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider (fetch JWKS, metadata, etc.)."""
        pass
    
    @abstractmethod
    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT access or ID token
            
        Returns:
            Decoded token claims
            
        Raises:
            AuthenticationError: If token is invalid
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user info from provider.
        
        Args:
            token: Access token
            
        Returns:
            User profile from OIDC userinfo endpoint
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """
        Refresh an access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens dict with access_token, id_token, refresh_token
        """
        pass
    
    # ==================== USER MANAGEMENT ====================
    
    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str | None = None,
        attributes: dict[str, Any] | None = None
    ) -> str:
        """
        Create a new user in the provider.
        
        Args:
            email: User email
            password: Optional password (if None, sends invite)
            attributes: Additional user attributes
            
        Returns:
            Provider user ID (sub)
        """
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user by ID from provider.
        
        Args:
            user_id: Provider user ID (sub)
            
        Returns:
            User attributes or None if not found
        """
        pass
    
    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        attributes: dict[str, Any]
    ) -> bool:
        """
        Update user attributes.
        
        Args:
            user_id: Provider user ID
            attributes: Attributes to update
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user from provider.
        
        Args:
            user_id: Provider user ID
            
        Returns:
            True if deleted
        """
        pass
    
    @abstractmethod
    async def disable_user(self, user_id: str) -> bool:
        """Disable user (soft delete)."""
        pass
    
    @abstractmethod
    async def enable_user(self, user_id: str) -> bool:
        """Re-enable a disabled user."""
        pass
    
    # ==================== MFA ====================
    
    @abstractmethod
    async def setup_mfa(self, user_id: str) -> dict[str, Any]:
        """
        Set up MFA for user.
        
        Returns:
            MFA setup details (secret, QR code URL, etc.)
        """
        pass
    
    @abstractmethod
    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code."""
        pass
    
    # ==================== HELPERS ====================
    
    def token_to_user(self, claims: dict[str, Any], tenant_id: str) -> User:
        """
        Convert token claims to User model.
        
        Override in subclasses for provider-specific claim mapping.
        """
        return User(
            sub=claims.get("sub"),
            email=claims.get("email", ""),
            email_verified=claims.get("email_verified", False),
            name=claims.get("name"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            tenant_id=tenant_id,
            tenant_roles={tenant_id: self._extract_roles(claims)},
        )
    
    def _extract_roles(self, claims: dict[str, Any]) -> list:
        """Extract roles from token claims."""
        # Override in subclasses - location varies by provider
        return claims.get("roles", [])


class AuthenticationError(Exception):
    """Authentication failed."""
    pass


class AuthorizationError(Exception):
    """Authorization denied."""
    pass
