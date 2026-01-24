"""OpenTelemetry tracing"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        logger.info("request", trace_id=trace_id, path=request.url.path)
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
