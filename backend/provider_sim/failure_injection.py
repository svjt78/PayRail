"""Failure injection configuration for provider simulation."""

from pydantic import BaseModel


class FailureConfig(BaseModel):
    timeout_rate: float = 0.0
    decline_rate: float = 0.05
    error_rate: float = 0.0
    duplicate_webhook_rate: float = 0.0
    settlement_mismatch_rate: float = 0.0
    latency_ms_min: int = 100
    latency_ms_max: int = 300


# Default profiles for each provider
PROVIDER_PROFILES = {
    "providerA": FailureConfig(
        decline_rate=0.05,
        latency_ms_min=100,
        latency_ms_max=300,
    ),
    "providerB": FailureConfig(
        decline_rate=0.10,
        latency_ms_min=200,
        latency_ms_max=500,
    ),
}

DECLINE_REASONS = {
    "providerA": ["insufficient_funds", "card_declined", "expired_card", "processing_error"],
    "providerB": ["DECLINED", "FRAUD", "EXPIRED", "DO_NOT_HONOR"],
}
