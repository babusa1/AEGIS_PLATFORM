"""OIDC Authentication Providers."""

from aegis_auth.providers.base import BaseAuthProvider
from aegis_auth.providers.cognito import CognitoProvider
from aegis_auth.providers.auth0 import Auth0Provider

__all__ = ["BaseAuthProvider", "CognitoProvider", "Auth0Provider"]
