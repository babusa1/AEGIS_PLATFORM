"""
Global Exception Handler for OncoLife Patient API.

This module provides centralized exception handling that:
- Catches all unhandled exceptions
- Converts exceptions to consistent JSON responses
- Logs errors with full context
- Hides internal details in production

Response Format:
    {
        "error": true,
        "error_code": "VALIDATION_ERROR",
        "message": "Human readable message",
        "details": { ... }  // Optional additional info
    }
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
import traceback

from core.exceptions import AppException
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.
    
    This should be called during app initialization to ensure
    all exceptions are handled consistently.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException
    ) -> JSONResponse:
        """
        Handle custom application exceptions.
        
        These are expected business errors with proper error codes
        and messages that should be returned to the client.
        """
        # Log the exception
        logger.warning(
            f"Application exception: {exc.error_code}",
            extra={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic/FastAPI validation errors.
        
        Converts validation errors to a user-friendly format
        with field-specific error messages.
        """
        # Parse validation errors into a clean format
        errors = {}
        for error in exc.errors():
            # Get field path (e.g., "body.email" or "query.page")
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors[field_path] = error["msg"]
        
        logger.warning(
            "Request validation failed",
            extra={
                "errors": errors,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": errors}
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle Starlette HTTP exceptions.
        
        These come from FastAPI/Starlette for things like:
        - 404 Not Found (missing routes)
        - 405 Method Not Allowed
        - 401 Unauthorized (from dependencies)
        """
        # Map common status codes to error codes
        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            408: "REQUEST_TIMEOUT",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }
        
        error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
        
        logger.warning(
            f"HTTP exception: {exc.status_code}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "error_code": error_code,
                "message": exc.detail or f"HTTP {exc.status_code} Error",
            }
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Handle all unhandled exceptions.
        
        This is the catch-all handler for unexpected errors.
        In production, it hides internal details from the client.
        In development, it can return more details for debugging.
        """
        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
            exc_info=True
        )
        
        # Build response based on environment
        if settings.is_development or settings.debug:
            # Include details in development
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "error_code": "INTERNAL_ERROR",
                    "message": f"{type(exc).__name__}: {str(exc)}",
                    "details": {
                        "traceback": traceback.format_exc().split("\n")
                    }
                }
            )
        else:
            # Hide details in production
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "error_code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                }
            )





