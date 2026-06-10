"""
Core Module - Doctor API
========================

This module contains the foundational infrastructure components:
- config: Centralized application configuration using Pydantic
- exceptions: Custom exception classes for consistent error handling
- logging: Structured logging configuration
- middleware: Request/response processing middleware

Usage:
    from core import settings, logger, AppException
    from core.middleware import setup_middleware
"""

from .config import settings, Settings
from .exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    DatabaseError,
    ExternalServiceError,
)
from .logging import setup_logging, get_logger

__all__ = [
    # Configuration
    "settings",
    "Settings",
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "DatabaseError",
    "ExternalServiceError",
    # Logging
    "setup_logging",
    "get_logger",
]





