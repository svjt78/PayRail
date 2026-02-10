"""API request models."""

from pydantic import BaseModel
from typing import Optional


class CreatePaymentRequest(BaseModel):
    amount: int
    currency: str = "USD"
    customer_email: Optional[str] = None
    description: Optional[str] = None
    pan: Optional[str] = None
    expiry: Optional[str] = None
    token: Optional[str] = None
    metadata: dict = {}


class AuthorizePaymentRequest(BaseModel):
    pan: Optional[str] = None
    expiry: Optional[str] = None
    token: Optional[str] = None


class CreateRefundRequest(BaseModel):
    payment_id: str
    amount: int
    reason: Optional[str] = None


class CreateDisputeRequest(BaseModel):
    payment_id: str
    amount: int
    reason: str


class SubmitEvidenceRequest(BaseModel):
    evidence: str


class ResolveDisputeRequest(BaseModel):
    outcome: str  # "won" or "lost"
