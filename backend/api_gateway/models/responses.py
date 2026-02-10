"""API response models."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    state: str
    merchant_id: str
    customer_email: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    token: Optional[str] = None
    provider_ref: Optional[str] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: str
    updated_at: str
    metadata: dict = {}


class RefundResponse(BaseModel):
    id: str
    payment_id: str
    amount: int
    currency: str
    state: str
    reason: Optional[str] = None
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    merchant_id: str
    correlation_id: Optional[str] = None
    created_at: str
    updated_at: str


class DisputeResponse(BaseModel):
    id: str
    payment_id: str
    amount: int
    state: str
    reason: str
    evidence: Optional[str] = None
    merchant_id: str
    correlation_id: Optional[str] = None
    created_at: str
    updated_at: str


class ListResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int
