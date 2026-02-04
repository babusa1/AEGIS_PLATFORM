"""
Structured Logging

Features:
- JSON-formatted logs
- Log levels
- Context propagation
- Log aggregation
"""

from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
import json
import sys
import traceback

import structlog
from pydantic import BaseModel, Field


# =============================================================================
# Log Models
# =============================================================================

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    """A structured log entry."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    
    # Context
    service: str = "aegis"
    component: Optional[str] = None
    
    # Trace context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    # Additional data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Error info
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Request context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None


# =============================================================================
# Structured Logger
# =============================================================================

class StructuredLogger:
    """
    Structured logger with JSON output.
    
    Features:
    - Automatic context binding
    - Log correlation with traces
    - Error tracking
    - Log aggregation support
    """
    
    def __init__(
        self,
        service: str = "aegis",
        component: str = None,
        min_level: LogLevel = LogLevel.INFO,
    ):
        self.service = service
        self.component = component
        self.min_level = min_level
        
        # Bound context
        self._context: Dict[str, Any] = {}
        
        # Log buffer (for aggregation)
        self._buffer: list[LogEntry] = []
        self._max_buffer = 1000
        
        # Configure structlog
        self._logger = structlog.get_logger(component or service)
    
    def bind(self, **kwargs) -> "StructuredLogger":
        """Bind context to logger."""
        new_logger = StructuredLogger(
            service=self.service,
            component=self.component,
            min_level=self.min_level,
        )
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if level should be logged."""
        levels = list(LogLevel)
        return levels.index(level) >= levels.index(self.min_level)
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        error: Exception = None,
        **kwargs,
    ):
        """Internal logging method."""
        if not self._should_log(level):
            return
        
        entry = LogEntry(
            level=level,
            message=message,
            service=self.service,
            component=self.component,
            data={**self._context, **kwargs},
        )
        
        # Add trace context if available
        from aegis.observability.tracing import get_tracer
        try:
            tracer = get_tracer()
            ctx = tracer.get_current_context()
            if ctx:
                entry.trace_id = ctx.trace_id
                entry.span_id = ctx.span_id
        except:
            pass
        
        # Add error info
        if error:
            entry.error_type = type(error).__name__
            entry.error_message = str(error)
            entry.stack_trace = traceback.format_exc()
        
        # Buffer for aggregation
        self._buffer.append(entry)
        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer:]
        
        # Output
        log_dict = entry.dict(exclude_none=True)
        
        if level == LogLevel.DEBUG:
            self._logger.debug(message, **log_dict)
        elif level == LogLevel.INFO:
            self._logger.info(message, **log_dict)
        elif level == LogLevel.WARNING:
            self._logger.warning(message, **log_dict)
        elif level == LogLevel.ERROR:
            self._logger.error(message, **log_dict)
        elif level == LogLevel.CRITICAL:
            self._logger.critical(message, **log_dict)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message."""
        self._log(LogLevel.ERROR, message, error=error, **kwargs)
    
    def critical(self, message: str, error: Exception = None, **kwargs):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, error=error, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with stack trace."""
        exc_info = sys.exc_info()
        if exc_info[1]:
            self.error(message, error=exc_info[1], **kwargs)
        else:
            self.error(message, **kwargs)
    
    def get_recent_logs(
        self,
        level: LogLevel = None,
        limit: int = 100,
        component: str = None,
    ) -> list[LogEntry]:
        """Get recent log entries."""
        logs = self._buffer
        
        if level:
            logs = [l for l in logs if l.level == level]
        
        if component:
            logs = [l for l in logs if l.component == component]
        
        return logs[-limit:]
    
    def search_logs(
        self,
        query: str,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Search logs by message content."""
        query_lower = query.lower()
        matching = [
            l for l in self._buffer
            if query_lower in l.message.lower()
        ]
        return matching[-limit:]


# Global logger
_logger: Optional[StructuredLogger] = None


def get_logger(component: str = None) -> StructuredLogger:
    """Get a structured logger."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    
    if component:
        return _logger.bind(component=component)
    return _logger
