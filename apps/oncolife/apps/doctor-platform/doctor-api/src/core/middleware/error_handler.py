"""
Global Error Handler - Doctor API
=================================

This module provides centralized exception handling for the FastAPI application.
Converts all exceptions to consistent JSON error responses.

Response format:
    {
        "error": true,
        "error_code": "ERROR_TYPE",
        "message": "Human-readable message",
        "details": { ... optional additional info ... }
    }

Usage:
    Applied automatically via setup_middleware()
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from core.exceptions import AppException
from core.logging import get_logger

logger = get_logger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """
        Handle custom application exceptions.
        
        These are expected errors with structured information.
        """
        logger.warning(
            f"Application error: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.
        
        Provides detailed information about which fields failed validation.
        """
        # Extract validation error details
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            f"Validation error on {request.url.path}",
            extra={
                "errors": errors,
                "path": request.url.path,
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
            },
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        """
        Handle standard HTTP exceptions (404, 405, etc.).
        
        Wraps them in our standard error response format.
        """
        # Map status codes to error codes
        error_codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
        }
        
        error_code = error_codes.get(exc.status_code, "HTTP_ERROR")
        
        if exc.status_code >= 500:
            logger.error(
                f"HTTP error {exc.status_code}: {exc.detail}",
                extra={"path": request.url.path}
            )
        else:
            logger.warning(
                f"HTTP error {exc.status_code}: {exc.detail}",
                extra={"path": request.url.path}
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "error_code": error_code,
                "message": str(exc.detail),
                "details": {},
            },
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """
        Handle SQLAlchemy database errors.
        
        Logs the full error but returns a generic message to avoid
        exposing database details.
        """
        logger.error(
            f"Database error on {request.url.path}: {str(exc)}",
            extra={"path": request.url.path},
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_code": "DATABASE_ERROR",
                "message": "A database error occurred. Please try again later.",
                "details": {},
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Catch-all handler for unexpected exceptions.
        
        Logs the full error with stack trace but returns a generic
        message to avoid exposing internal details.
        """
        logger.error(
            f"Unexpected error on {request.url.path}: {str(exc)}",
            extra={"path": request.url.path},
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": {},
            },
        )





