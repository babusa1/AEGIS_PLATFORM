"""
Auth Provider Factory
"""

from enum import Enum
from typing import Any
import structlog

from aegis_auth.providers.base import BaseAuthProvider
from aegis_auth.providers.cognito import CognitoProvider
from aegis_auth.providers.auth0 import Auth0Provider

logger = structlog.get_logger(__name__)


class AuthProviderType(str, Enum):
    COGNITO = "cognito"
    AUTH0 = "auth0"
    OKTA = "okta"
    CUSTOM = "custom"


class AuthProvider:
    """Auth Provider Factory."""
    
    _providers: dict[str, type[BaseAuthProvider]] = {
        AuthProviderType.COGNITO: CognitoProvider,
        AuthProviderType.AUTH0: Auth0Provider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: str | AuthProviderType,
        issuer_url: str,
        client_id: str,
        client_secret: str | None = None,
        **kwargs
    ) -> BaseAuthProvider:
        if isinstance(provider_type, str):
            provider_type = AuthProviderType(provider_type.lower())
        
        provider_class = cls._providers.get(provider_type)
        
        if provider_class is None:
            raise ValueError(f"Unsupported provider: {provider_type}")
        
        return provider_class(
            issuer_url=issuer_url,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs
        )
    
    @classmethod
    def from_config(cls, config: Any) -> BaseAuthProvider:
        if hasattr(config, "auth"):
            auth_config = config.auth
        elif isinstance(config, dict):
            auth_config = config.get("auth", config)
        else:
            auth_config = config
        
        provider_type = auth_config.get("provider", "cognito")
        issuer_url = auth_config.get("issuer_url")
        client_id = auth_config.get("client_id")
        client_secret = auth_config.get("client_secret")
        
        return cls.create(
            provider_type=provider_type,
            issuer_url=issuer_url,
            client_id=client_id,
            client_secret=client_secret,
        )


_auth_provider: BaseAuthProvider | None = None


async def get_auth_provider(config: Any = None) -> BaseAuthProvider:
    global _auth_provider
    
    if _auth_provider is None:
        if config is None:
            raise ValueError("No config provided")
        
        _auth_provider = AuthProvider.from_config(config)
        await _auth_provider.initialize()
    
    return _auth_provider
