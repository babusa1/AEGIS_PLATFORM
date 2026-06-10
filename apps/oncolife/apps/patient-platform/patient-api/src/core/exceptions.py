"""
Custom Exception Classes for OncoLife Patient API.

This module defines a hierarchy of custom exceptions that provide:
- Consistent error responses across the API
- HTTP status code mapping
- Error codes for client-side handling
- Detailed error messages for debugging

Exception Hierarchy:
    AppException (base)
    ├── ValidationException (400)
    ├── AuthenticationException (401)
    ├── AuthorizationException (403)
    ├── NotFoundException (404)
    ├── ConflictException (409)
    ├── RateLimitException (429)
    ├── DatabaseException (500)
    └── ExternalServiceException (502)

Usage:
    from core.exceptions import NotFoundException, ValidationException
    
    # Raise with message
    raise NotFoundException("Patient not found")
    
    # Raise with details
    raise ValidationException(
        message="Invalid input",
        details={"field": "email", "error": "Invalid format"}
    )
"""

from typing import Any, Dict, Optional
from http import HTTPStatus


class AppException(Exception):
    """
    Base exception class for all application exceptions.
    
    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for the response
        error_code: Machine-readable error code for client handling
        details: Additional error details (field errors, context, etc.)
    """
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            error_code: Machine-readable error code
            details: Additional error context
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for JSON response.
        
        Returns:
            Dictionary with error details
        """
        response = {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"status_code={self.status_code}, "
            f"error_code='{self.error_code}')"
        )


class ValidationException(AppException):
    """
    Exception for request validation errors (400 Bad Request).
    
    Use when:
    - Request body fails Pydantic validation
    - Required fields are missing
    - Field values are invalid format
    - Business rule validation fails
    
    Example:
        raise ValidationException(
            message="Invalid patient data",
            details={"email": "Invalid email format"}
        )
    """
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            error_code=error_code,
            details=details,
        )


class AuthenticationException(AppException):
    """
    Exception for authentication failures (401 Unauthorized).
    
    Use when:
    - No authentication token provided
    - Token is expired or invalid
    - Credentials are incorrect
    
    Example:
        raise AuthenticationException("Invalid or expired token")
    """
    
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "AUTHENTICATION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code=error_code,
            details=details,
        )


class AuthorizationException(AppException):
    """
    Exception for authorization failures (403 Forbidden).
    
    Use when:
    - User is authenticated but lacks permission
    - Resource access is denied
    - Role-based access control fails
    
    Example:
        raise AuthorizationException("You don't have permission to access this resource")
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "AUTHORIZATION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code=error_code,
            details=details,
        )


class NotFoundException(AppException):
    """
    Exception for resource not found errors (404 Not Found).
    
    Use when:
    - Requested resource doesn't exist
    - Database query returns no results
    - Referenced entity is missing
    
    Example:
        raise NotFoundException(f"Patient with ID {patient_id} not found")
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code=error_code,
            details=details,
        )


class ConflictException(AppException):
    """
    Exception for resource conflict errors (409 Conflict).
    
    Use when:
    - Duplicate resource creation attempted
    - Unique constraint violation
    - Concurrent modification conflict
    
    Example:
        raise ConflictException("A patient with this email already exists")
    """
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "CONFLICT",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code=error_code,
            details=details,
        )


class RateLimitException(AppException):
    """
    Exception for rate limit exceeded (429 Too Many Requests).
    
    Use when:
    - API rate limit is exceeded
    - Too many requests in time window
    
    Example:
        raise RateLimitException("Rate limit exceeded. Try again in 60 seconds.")
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None,
    ) -> None:
        if retry_after:
            details = details or {}
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error_code=error_code,
            details=details,
        )


class DatabaseException(AppException):
    """
    Exception for database-related errors (500 Internal Server Error).
    
    Use when:
    - Database connection fails
    - Query execution fails
    - Transaction errors occur
    
    Note: Don't expose internal database details to clients.
    
    Example:
        raise DatabaseException("Unable to process request. Please try again.")
    """
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "DATABASE_ERROR",
        original_error: Optional[Exception] = None,
    ) -> None:
        # Store original error for logging but don't expose to client
        self.original_error = original_error
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
        )


class ExternalServiceException(AppException):
    """
    Exception for external service failures (502 Bad Gateway).
    
    Use when:
    - External API call fails
    - Third-party service is unavailable
    - Integration errors occur
    
    Example:
        raise ExternalServiceException("Unable to connect to email service")
    """
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
    ) -> None:
        if service_name:
            details = details or {}
            details["service"] = service_name
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_GATEWAY,
            error_code=error_code,
            details=details,
        )


class BusinessRuleException(AppException):
    """
    Exception for business rule violations (422 Unprocessable Entity).
    
    Use when:
    - Business logic rules are violated
    - Operation is valid syntactically but not semantically
    - Domain-specific constraints are not met
    
    Example:
        raise BusinessRuleException(
            "Cannot schedule appointment in the past",
            error_code="INVALID_APPOINTMENT_TIME"
        )
    """
    
    def __init__(
        self,
        message: str = "Business rule violation",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "BUSINESS_RULE_VIOLATION",
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            error_code=error_code,
            details=details,
        )


# =============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# =============================================================================
# Some code uses "Error" suffix instead of "Exception" suffix.
# These aliases maintain backward compatibility.

NotFoundError = NotFoundException
ValidationError = ValidationException
ExternalServiceError = ExternalServiceException
AuthenticationError = AuthenticationException
AuthorizationError = AuthorizationException
ConflictError = ConflictException
DatabaseError = DatabaseException
RateLimitError = RateLimitException
BusinessRuleError = BusinessRuleException

