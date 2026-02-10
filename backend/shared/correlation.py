"""Correlation ID management for distributed tracing."""

import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    return f"corr_{uuid.uuid4().hex[:16]}"


def get_correlation_id() -> str:
    cid = correlation_id_var.get()
    if not cid:
        cid = generate_correlation_id()
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    correlation_id_var.set(cid)
