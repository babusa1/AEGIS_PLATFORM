"""
OpenTelemetry Distributed Tracing

Features:
- Automatic span creation
- Context propagation
- Custom attributes
- Trace sampling
- Export to Jaeger/Zipkin/OTLP
"""

from typing import Any, Callable, Optional
from datetime import datetime
from enum import Enum
from functools import wraps
import asyncio
import uuid
import json
import time
from contextlib import contextmanager

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Try to import OpenTelemetry (optional dependency)
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Using fallback tracing.")


# =============================================================================
# Span Models
# =============================================================================

class SpanKind(str, Enum):
    """Types of spans."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Span status."""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


class Span(BaseModel):
    """A trace span."""
    trace_id: str
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:16])
    parent_span_id: Optional[str] = None
    
    name: str
    kind: SpanKind = SpanKind.INTERNAL
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Status
    status: SpanStatus = SpanStatus.UNSET
    error_message: Optional[str] = None
    
    # Attributes
    attributes: dict = Field(default_factory=dict)
    
    # Events
    events: list[dict] = Field(default_factory=list)
    
    def end(self, status: SpanStatus = SpanStatus.OK, error: str = None):
        """End the span."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        if error:
            self.error_message = error
            self.status = SpanStatus.ERROR
    
    def add_event(self, name: str, attributes: dict = None):
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value


class TraceContext(BaseModel):
    """Propagated trace context."""
    trace_id: str
    span_id: str
    trace_flags: int = 1  # Sampled
    trace_state: str = ""


# =============================================================================
# Tracer
# =============================================================================

class Tracer:
    """
    Distributed tracer with OpenTelemetry support.
    
    Falls back to in-memory tracing when OTel is not available.
    """
    
    def __init__(
        self,
        service_name: str = "aegis-orchestrator",
        otlp_endpoint: str = None,
        sample_rate: float = 1.0,
    ):
        self.service_name = service_name
        self.sample_rate = sample_rate
        
        # Active spans (for context propagation)
        self._active_spans: dict[str, Span] = {}
        
        # Completed traces (for in-memory fallback)
        self._traces: dict[str, list[Span]] = {}
        self._max_traces = 1000
        
        # Current context (thread-local in production)
        self._current_trace_id: Optional[str] = None
        self._current_span_id: Optional[str] = None
        
        # Initialize OpenTelemetry if available
        self._otel_tracer = None
        if OTEL_AVAILABLE:
            self._init_otel(otlp_endpoint)
    
    def _init_otel(self, otlp_endpoint: str = None):
        """Initialize OpenTelemetry."""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": "development",
        })
        
        provider = TracerProvider(resource=resource)
        
        # Add exporters
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        else:
            # Console exporter for development
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        
        otel_trace.set_tracer_provider(provider)
        self._otel_tracer = otel_trace.get_tracer(self.service_name)
        
        logger.info("OpenTelemetry initialized", service=self.service_name)
    
    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict = None,
        parent_context: TraceContext = None,
    ):
        """
        Start a new span (context manager).
        
        Usage:
            with tracer.start_span("my-operation") as span:
                span.set_attribute("key", "value")
                # do work
        """
        # Determine trace ID
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        elif self._current_trace_id:
            trace_id = self._current_trace_id
            parent_span_id = self._current_span_id
        else:
            trace_id = str(uuid.uuid4()).replace("-", "")
            parent_span_id = None
        
        # Create span
        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        
        # Set as current
        old_trace_id = self._current_trace_id
        old_span_id = self._current_span_id
        self._current_trace_id = trace_id
        self._current_span_id = span.span_id
        self._active_spans[span.span_id] = span
        
        try:
            yield span
            span.end(SpanStatus.OK)
        except Exception as e:
            span.end(SpanStatus.ERROR, str(e))
            raise
        finally:
            # Restore context
            self._current_trace_id = old_trace_id
            self._current_span_id = old_span_id
            self._active_spans.pop(span.span_id, None)
            
            # Store completed span
            self._store_span(span)
    
    def _store_span(self, span: Span):
        """Store completed span."""
        trace_id = span.trace_id
        
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        
        self._traces[trace_id].append(span)
        
        # Cleanup old traces
        if len(self._traces) > self._max_traces:
            oldest = list(self._traces.keys())[0]
            del self._traces[oldest]
    
    def get_current_context(self) -> Optional[TraceContext]:
        """Get current trace context for propagation."""
        if self._current_trace_id and self._current_span_id:
            return TraceContext(
                trace_id=self._current_trace_id,
                span_id=self._current_span_id,
            )
        return None
    
    def inject_context(self, headers: dict) -> dict:
        """Inject trace context into headers for propagation."""
        context = self.get_current_context()
        if context:
            # W3C Trace Context format
            headers["traceparent"] = f"00-{context.trace_id}-{context.span_id}-01"
            if context.trace_state:
                headers["tracestate"] = context.trace_state
        return headers
    
    def extract_context(self, headers: dict) -> Optional[TraceContext]:
        """Extract trace context from headers."""
        traceparent = headers.get("traceparent")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                return TraceContext(
                    trace_id=parts[1],
                    span_id=parts[2],
                    trace_flags=int(parts[3], 16),
                )
        return None
    
    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace."""
        return self._traces.get(trace_id, [])
    
    def get_recent_traces(self, limit: int = 100) -> list[dict]:
        """Get recent traces with summary."""
        traces = []
        for trace_id, spans in list(self._traces.items())[-limit:]:
            root_span = next((s for s in spans if not s.parent_span_id), spans[0] if spans else None)
            traces.append({
                "trace_id": trace_id,
                "name": root_span.name if root_span else "unknown",
                "span_count": len(spans),
                "duration_ms": root_span.duration_ms if root_span else 0,
                "status": root_span.status.value if root_span else "unknown",
                "start_time": root_span.start_time.isoformat() if root_span else None,
            })
        return traces


# =============================================================================
# Decorators
# =============================================================================

# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def trace(
    name: str = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict = None,
):
    """
    Decorator to trace a function.
    
    Usage:
        @trace("my-function")
        def my_function():
            pass
    """
    def decorator(func: Callable):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_span(span_name, kind, attributes) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_async(
    name: str = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict = None,
):
    """
    Decorator to trace an async function.
    
    Usage:
        @trace_async("my-async-function")
        async def my_function():
            pass
    """
    def decorator(func: Callable):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_span(span_name, kind, attributes) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# Middleware
# =============================================================================

class TracingMiddleware:
    """FastAPI middleware for automatic request tracing."""
    
    def __init__(self, app, tracer: Tracer = None):
        self.app = app
        self.tracer = tracer or get_tracer()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract context from headers
        headers = dict(scope.get("headers", []))
        headers = {k.decode(): v.decode() for k, v in headers.items()}
        parent_context = self.tracer.extract_context(headers)
        
        # Create request span
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        
        with self.tracer.start_span(
            f"{method} {path}",
            kind=SpanKind.SERVER,
            parent_context=parent_context,
        ) as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.path", path)
            span.set_attribute("http.scheme", scope.get("scheme", "http"))
            
            # Capture response status
            status_code = 200
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 200)
                    span.set_attribute("http.status_code", status_code)
                    if status_code >= 400:
                        span.status = SpanStatus.ERROR
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
