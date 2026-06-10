"""
Custom Exceptions - Doctor API
==============================

This module defines a hierarchy of custom exceptions for consistent
error handling throughout the application.

Exception Hierarchy:
    AppException (base)
    ├── AuthenticationError (401)
    ├── AuthorizationError (403)
    ├── NotFoundError (404)
    ├── ValidationError (422)
    ├── ConflictError (409)
    ├── DatabaseError (500)
    └── ExternalServiceError (502)

Usage:
    from core.exceptions import NotFoundError, ValidationError
    
    raise NotFoundError(
        message="Patient not found",
        details={"patient_id": patient_id}
    )
"""

from typing import Any, Dict, Optional
from http import HTTPStatus


class AppException(Exception):
    """
    Base exception class for all application errors.
    
    All custom exceptions inherit from this class, providing
    consistent error handling and HTTP status code mapping.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for API responses
        error_code: Machine-readable error code for client handling
        details: Additional context about the error
    """
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API response.
        
        Returns:
            Dictionary containing error information
        """
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"{self.error_code}: {self.message}"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"status_code={self.status_code}, "
            f"error_code='{self.error_code}')"
        )


class AuthenticationError(AppException):
    """
    Raised when authentication fails.
    
    Examples:
        - Invalid or expired token
        - Missing authentication header
        - Invalid credentials
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(AppException):
    """
    Raised when the user lacks permission for an action.
    
    Examples:
        - User trying to access another user's data
        - Staff trying to access admin-only features
        - Insufficient role/permissions
    """
    
    def __init__(
        self,
        message: str = "You don't have permission to perform this action",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundError(AppException):
    """
    Raised when a requested resource doesn't exist.
    
    Examples:
        - Patient not found
        - Clinic not found
        - Staff member not found
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = str(resource_id)
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code="NOT_FOUND",
            details=error_details,
        )


class ValidationError(AppException):
    """
    Raised when input validation fails.
    
    Examples:
        - Invalid email format
        - Missing required fields
        - Value out of allowed range
    """
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class ConflictError(AppException):
    """
    Raised when there's a conflict with existing data.
    
    Examples:
        - Duplicate email address
        - Staff already associated with clinic
        - Resource already exists
    """
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code="CONFLICT_ERROR",
            details=details,
        )


class DatabaseError(AppException):
    """
    Raised when a database operation fails.
    
    Examples:
        - Connection timeout
        - Query execution failure
        - Transaction rollback
    
    Note: Be careful not to expose sensitive database details in the message.
    """
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=error_details,
        )


class ExternalServiceError(AppException):
    """
    Raised when an external service (AWS, Cognito, etc.) fails.
    
    Examples:
        - Cognito authentication failure
        - AWS service timeout
        - Third-party API error
    """
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if service_name:
            error_details["service"] = service_name
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
        )


class RateLimitError(AppException):
    """
    Raised when rate limit is exceeded.
    
    Examples:
        - Too many API requests
        - Too many login attempts
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after_seconds"] = retry_after
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
        )





