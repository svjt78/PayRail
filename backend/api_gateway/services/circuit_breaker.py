"""File-backed circuit breaker for provider failover."""

import os
from datetime import datetime, timedelta
from shared.file_store import FileStore
from shared.models import CircuitState

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


class ProviderUnavailableError(Exception):
    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        super().__init__(f"Provider {provider_id} circuit is OPEN")


class CircuitBreaker:

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.state_path = os.path.join(DATA_DIR, "providers", f"{provider_id}_state.json")
        self.failure_threshold = int(os.environ.get("CB_FAILURE_THRESHOLD", 5))
        self.recovery_timeout = int(os.environ.get("CB_RECOVERY_TIMEOUT", 30))
        self.half_open_max = int(os.environ.get("CB_HALF_OPEN_MAX_CALLS", 3))

    def _read_state(self) -> dict:
        return FileStore.read_json(self.state_path, default={
            "provider_id": self.provider_id,
            "circuit_state": CircuitState.CLOSED.value,
            "failure_count": 0,
            "success_count": 0,
            "half_open_calls": 0,
        })

    def _write_state(self, state: dict):
        FileStore.write_json(self.state_path, state)

    def can_execute(self) -> bool:
        state = self._read_state()
        circuit = state.get("circuit_state", CircuitState.CLOSED.value)

        if circuit == CircuitState.CLOSED.value:
            return True

        if circuit == CircuitState.OPEN.value:
            opened_at = state.get("opened_at")
            if opened_at:
                opened = datetime.fromisoformat(opened_at)
                if datetime.utcnow() - opened > timedelta(seconds=self.recovery_timeout):
                    # Transition to half-open
                    state["circuit_state"] = CircuitState.HALF_OPEN.value
                    state["half_open_calls"] = 0
                    self._write_state(state)
                    return True
            return False

        if circuit == CircuitState.HALF_OPEN.value:
            if state.get("half_open_calls", 0) < self.half_open_max:
                return True
            return False

        return True

    def record_success(self):
        state = self._read_state()
        circuit = state.get("circuit_state", CircuitState.CLOSED.value)

        state["success_count"] = state.get("success_count", 0) + 1
        state["last_success_at"] = datetime.utcnow().isoformat()

        if circuit == CircuitState.HALF_OPEN.value:
            state["half_open_calls"] = state.get("half_open_calls", 0) + 1
            if state["half_open_calls"] >= self.half_open_max:
                # Close the circuit
                state["circuit_state"] = CircuitState.CLOSED.value
                state["failure_count"] = 0
                state["half_open_calls"] = 0

        self._write_state(state)

    def record_failure(self):
        state = self._read_state()
        circuit = state.get("circuit_state", CircuitState.CLOSED.value)

        state["failure_count"] = state.get("failure_count", 0) + 1
        state["last_failure_at"] = datetime.utcnow().isoformat()

        if circuit == CircuitState.HALF_OPEN.value:
            # Immediately re-open
            state["circuit_state"] = CircuitState.OPEN.value
            state["opened_at"] = datetime.utcnow().isoformat()
            state["half_open_calls"] = 0
        elif circuit == CircuitState.CLOSED.value:
            if state["failure_count"] >= self.failure_threshold:
                state["circuit_state"] = CircuitState.OPEN.value
                state["opened_at"] = datetime.utcnow().isoformat()

        self._write_state(state)

    def get_state(self) -> dict:
        return self._read_state()
