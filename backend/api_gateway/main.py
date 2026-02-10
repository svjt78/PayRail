"""PayRail API Gateway - Main application entry point."""

import os
import sys
import logging

# Keep /app first so local packages like "models" resolve correctly.
sys.path.append("/app/shared")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.middleware import CorrelationMiddleware, RBACMiddleware, MetricsMiddleware

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(
    title="PayRail API Gateway",
    version="1.0.0",
    description="Production-grade payment gateway demo",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (outermost first in execution order)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RBACMiddleware)
app.add_middleware(CorrelationMiddleware)

# Initialize data directories on startup
@app.on_event("startup")
async def startup():
    data_dir = os.environ.get("DATA_DIR", "/app/data")
    for d in ["ledger", "vault", "providers", "settlement", "metrics",
              "outbox", "idempotency", "reconciliation"]:
        os.makedirs(os.path.join(data_dir, d), exist_ok=True)
    logging.getLogger("payrail").info("API Gateway started, data dirs initialized")

# Import and mount routers
from routers import payments, refunds, disputes, webhooks, health, audit

app.include_router(payments.router, prefix="/payment-intents", tags=["Payments"])
app.include_router(refunds.router, prefix="/refunds", tags=["Refunds"])
app.include_router(disputes.router, prefix="/disputes", tags=["Disputes"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(health.router, tags=["Health"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
