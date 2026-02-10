"""Shared middleware for correlation IDs, RBAC, and metrics."""

import time
import json
import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.correlation import set_correlation_id, generate_correlation_id, get_correlation_id
from shared.file_store import FileStore

logger = logging.getLogger("payrail")


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-Id", generate_correlation_id())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response


class RBACMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        if request.url.path.startswith("/webhooks/"):
            return await call_next(request)
        # Allow GET without merchant header for read operations
        if request.method == "GET":
            return await call_next(request)
        merchant_id = request.headers.get("X-Merchant-Id")
        if not merchant_id and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return JSONResponse(
                status_code=401,
                content={"error": "X-Merchant-Id header required"},
            )
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)
        data_dir = os.environ.get("DATA_DIR", "/app/data")
        metrics_path = os.path.join(data_dir, "metrics", "service_metrics.jsonl")
        try:
            FileStore.append_jsonl(metrics_path, {
                "timestamp": time.time(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "correlation_id": get_correlation_id(),
            })
        except Exception:
            pass  # Don't fail requests over metrics
        return response
