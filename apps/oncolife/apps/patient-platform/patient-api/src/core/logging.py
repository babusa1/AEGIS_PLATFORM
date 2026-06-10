"""
Structured Logging Configuration for OncoLife Patient API.

This module provides:
- Structured JSON logging for production
- Human-readable logging for development
- Correlation ID support for request tracing
- Performance logging helpers
- Context-aware logging

Features:
- JSON format for easy log aggregation (ELK, CloudWatch, etc.)
- Request correlation IDs for tracing
- Automatic context inclusion (timestamp, level, module)
- Performance timing decorators

Usage:
    from core.logging import get_logger, setup_logging
    
    # Setup logging at app startup
    setup_logging()
    
    # Get a logger for your module
    logger = get_logger(__name__)
    
    # Log messages
    logger.info("Processing request", extra={"patient_id": 123})
    logger.error("Failed to save", exc_info=True)
"""

import logging
import logging.config
import sys
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from functools import wraps
from contextvars import ContextVar

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    correlation_id_var.set(correlation_id)


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Produces JSON-formatted log records suitable for log aggregation
    systems like ELK Stack, AWS CloudWatch, or Datadog.
    
    Output format:
        {
            "timestamp": "2024-01-15T10:30:00.000Z",
            "level": "INFO",
            "logger": "core.services.patient",
            "message": "Patient created successfully",
            "correlation_id": "abc-123",
            "extra": { ... }
        }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields passed to the logger
        # Exclude standard LogRecord attributes
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "message", "taskName"
        }
        
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_attrs and not key.startswith("_")
        }
        
        if extra:
            log_data["extra"] = extra
        
        return json.dumps(log_data, default=str)


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable formatter for development environment.
    
    Produces colorized, easy-to-read log output for local development.
    
    Output format:
        2024-01-15 10:30:00 | INFO     | module.name | Message here
    """
    
    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        # Get color for level
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build the log message
        correlation_id = get_correlation_id()
        correlation_str = f" [{correlation_id[:8]}]" if correlation_id else ""
        
        formatted = (
            f"{timestamp} | "
            f"{color}{record.levelname:8}{reset} | "
            f"{record.name}{correlation_str} | "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    app_name: str = "oncolife-api"
) -> None:
    """
    Configure application logging.
    
    Should be called once at application startup, typically in main.py.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format - "json" for production, "text" for development
        app_name: Application name for log identification
    
    Example:
        # In main.py
        from core.logging import setup_logging
        from core.config import settings
        
        setup_logging(
            level=settings.log_level,
            format_type=settings.log_format
        )
    """
    # Determine formatter based on format type
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = DevelopmentFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            "app_name": app_name,
            "log_level": level,
            "log_format": format_type
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.
    
    Args:
        name: Logger name, typically __name__
    
    Returns:
        Configured logger instance
    
    Example:
        from core.logging import get_logger
        
        logger = get_logger(__name__)
        logger.info("Starting operation")
    """
    return logging.getLogger(name)


def log_execution_time(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    message: str = "Execution completed"
) -> Callable:
    """
    Decorator to log function execution time.
    
    Useful for performance monitoring and identifying slow operations.
    
    Args:
        logger: Logger instance (uses function's module logger if None)
        level: Log level for the timing message
        message: Custom message prefix
    
    Example:
        @log_execution_time(message="Database query")
        async def fetch_patients():
            ...
    """
    def decorator(func: Callable) -> Callable:
        func_logger = logger or get_logger(func.__module__)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start_time) * 1000
                func_logger.log(
                    level,
                    f"{message}: {func.__name__}",
                    extra={"execution_time_ms": round(elapsed, 2)}
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start_time) * 1000
                func_logger.log(
                    level,
                    f"{message}: {func.__name__}",
                    extra={"execution_time_ms": round(elapsed, 2)}
                )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator





