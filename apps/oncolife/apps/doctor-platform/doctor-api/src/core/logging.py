"""
Logging Configuration - Doctor API
===================================

This module provides structured logging configuration for the application.
Supports both JSON format (for production) and text format (for development).

Features:
- Structured logging with consistent fields
- Request correlation ID support
- Environment-aware log levels
- Performance-optimized for production

Usage:
    from core.logging import get_logger, setup_logging
    
    # Setup logging at application startup
    setup_logging()
    
    # Get a logger for a module
    logger = get_logger(__name__)
    logger.info("Processing request", extra={"patient_id": "123"})
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

from .config import settings

# Context variable for request correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON for structured logging.
    
    This format is ideal for log aggregation systems like CloudWatch,
    ELK stack, or Datadog.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.app_name,
            "environment": settings.environment,
        }
        
        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Add source location for debugging
        if settings.debug:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields passed to the logger
        if hasattr(record, "__dict__"):
            extra_fields = {
                key: value
                for key, value in record.__dict__.items()
                if key not in {
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "message", "taskName"
                }
                and not key.startswith("_")
            }
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter for development and debugging.
    
    Output format:
        [2024-01-15 10:30:45] INFO [module.name] Message here | extra_field=value
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a human-readable string.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        # Timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Level with color (if terminal supports it)
        level = record.levelname
        if sys.stderr.isatty():
            color = self.COLORS.get(level, "")
            level = f"{color}{level:8}{self.RESET}"
        else:
            level = f"{level:8}"
        
        # Base message
        message = f"[{timestamp}] {level} [{record.name}] {record.getMessage()}"
        
        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            message = f"{message} | correlation_id={correlation_id}"
        
        # Add extra fields
        if hasattr(record, "__dict__"):
            extra_fields = {
                key: value
                for key, value in record.__dict__.items()
                if key not in {
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "message", "taskName"
                }
                and not key.startswith("_")
            }
            if extra_fields:
                extras = " | ".join(f"{k}={v}" for k, v in extra_fields.items())
                message = f"{message} | {extras}"
        
        # Add exception info if present
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        
        return message


def setup_logging() -> None:
    """
    Configure application logging based on settings.
    
    Should be called once at application startup.
    """
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Choose formatter based on settings
    if settings.log_format.lower() == "json" and settings.is_production:
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"format={settings.log_format}, environment={settings.environment}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"key": "value"})
    """
    return logging.getLogger(name)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current request context.
    
    Args:
        correlation_id: Unique identifier for the request
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Get the correlation ID for the current request context.
    
    Returns:
        The correlation ID, or None if not set
    """
    return correlation_id_var.get()





