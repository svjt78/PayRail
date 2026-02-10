"""State machine validation for payments, refunds, and disputes."""

from shared.models import (
    PaymentState, RefundState, DisputeState,
    PAYMENT_TRANSITIONS, REFUND_TRANSITIONS, DISPUTE_TRANSITIONS,
)


class InvalidTransitionError(Exception):
    def __init__(self, entity_type: str, current: str, target: str):
        self.entity_type = entity_type
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid {entity_type} transition: {current} -> {target}"
        )


def validate_payment_transition(current: str, target: str) -> bool:
    current_state = PaymentState(current)
    target_state = PaymentState(target)
    allowed = PAYMENT_TRANSITIONS.get(current_state, [])
    if target_state not in allowed:
        raise InvalidTransitionError("payment", current, target)
    return True


def validate_refund_transition(current: str, target: str) -> bool:
    current_state = RefundState(current)
    target_state = RefundState(target)
    allowed = REFUND_TRANSITIONS.get(current_state, [])
    if target_state not in allowed:
        raise InvalidTransitionError("refund", current, target)
    return True


def validate_dispute_transition(current: str, target: str) -> bool:
    current_state = DisputeState(current)
    target_state = DisputeState(target)
    allowed = DISPUTE_TRANSITIONS.get(current_state, [])
    if target_state not in allowed:
        raise InvalidTransitionError("dispute", current, target)
    return True
