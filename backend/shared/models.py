"""Domain models, state machines, and enums shared across all services."""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid


# === Enums ===

class PaymentState(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    SETTLED = "settled"
    DECLINED = "declined"
    REVERSED = "reversed"
    CHARGEBACK = "chargeback"


class RefundState(str, Enum):
    CREATED = "created"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DisputeState(str, Enum):
    OPENED = "opened"
    UNDER_REVIEW = "under_review"
    WON = "won"
    LOST = "lost"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# === State Machine Transitions ===

PAYMENT_TRANSITIONS: dict[PaymentState, list[PaymentState]] = {
    PaymentState.CREATED: [PaymentState.AUTHORIZED, PaymentState.DECLINED],
    PaymentState.AUTHORIZED: [PaymentState.CAPTURED, PaymentState.REVERSED],
    PaymentState.CAPTURED: [PaymentState.SETTLED, PaymentState.CHARGEBACK],
    PaymentState.SETTLED: [],
    PaymentState.DECLINED: [],
    PaymentState.REVERSED: [],
    PaymentState.CHARGEBACK: [],
}

REFUND_TRANSITIONS: dict[RefundState, list[RefundState]] = {
    RefundState.CREATED: [RefundState.PENDING_APPROVAL],
    RefundState.PENDING_APPROVAL: [RefundState.APPROVED, RefundState.FAILED],
    RefundState.APPROVED: [RefundState.SUCCEEDED, RefundState.FAILED],
    RefundState.SUCCEEDED: [],
    RefundState.FAILED: [],
}

DISPUTE_TRANSITIONS: dict[DisputeState, list[DisputeState]] = {
    DisputeState.OPENED: [DisputeState.UNDER_REVIEW],
    DisputeState.UNDER_REVIEW: [DisputeState.WON, DisputeState.LOST],
    DisputeState.WON: [],
    DisputeState.LOST: [],
}


# === Domain Models ===

class PaymentIntent(BaseModel):
    id: str = Field(default_factory=lambda: f"pi_{uuid.uuid4().hex[:12]}")
    amount: int
    currency: str = "USD"
    state: PaymentState = PaymentState.CREATED
    merchant_id: str
    customer_email: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    token: Optional[str] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    provider_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Refund(BaseModel):
    id: str = Field(default_factory=lambda: f"ref_{uuid.uuid4().hex[:12]}")
    payment_id: str
    amount: int
    currency: str = "USD"
    state: RefundState = RefundState.CREATED
    reason: Optional[str] = None
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    merchant_id: str
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Dispute(BaseModel):
    id: str = Field(default_factory=lambda: f"dsp_{uuid.uuid4().hex[:12]}")
    payment_id: str
    amount: int
    state: DisputeState = DisputeState.OPENED
    reason: str
    evidence: Optional[str] = None
    merchant_id: str
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LedgerEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    type: str
    ref: str
    amount: int
    currency: str = "USD"
    merchant_id: str
    provider: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class OutboxEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"oevt_{uuid.uuid4().hex[:12]}")
    type: str
    payload: dict
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderStateModel(BaseModel):
    provider_id: str
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    half_open_calls: int = 0
