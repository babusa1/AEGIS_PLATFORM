"""
Core Infrastructure Module for OncoLife Patient API.

This module provides the foundational infrastructure components:
- Configuration management (Pydantic Settings)
- Logging infrastructure (structured logging)
- Exception handling (custom exceptions)
- Middleware (error handling, request logging, correlation IDs)

Usage:
    from core import settings, logger, AppException
    from core.middleware import setup_middleware
"""

from .config import settings, Settings
from .exceptions import (
    AppException,
    ValidationException,
    NotFoundException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    ExternalServiceException,
)
from .logging import setup_logging, get_logger

__all__ = [
    # Configuration
    "settings",
    "Settings",
    # Exceptions
    "AppException",
    "ValidationException",
    "NotFoundException",
    "AuthenticationException",
    "AuthorizationException",
    "DatabaseException",
    "ExternalServiceException",
    # Logging
    "setup_logging",
    "get_logger",
]





