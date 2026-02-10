"""Idempotency key management - prevents duplicate payment processing."""

import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
from shared.file_store import FileStore

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
KEYS_PATH = os.path.join(DATA_DIR, "idempotency", "idempotency_keys.json")
TTL_HOURS = 24


class IdempotencyConflictError(Exception):
    pass


class CachedResponse:
    def __init__(self, response: dict, status_code: int):
        self.response = response
        self.status_code = status_code


class IdempotencyService:

    @staticmethod
    def compute_hash(body: dict) -> str:
        serialized = json.dumps(body, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def check(self, key: str, request_hash: str) -> Optional[CachedResponse]:
        keys = FileStore.read_json(KEYS_PATH, default={})
        if key not in keys:
            return None

        stored = keys[key]
        if stored["request_hash"] != request_hash:
            raise IdempotencyConflictError(
                f"Idempotency key '{key}' already used with different request body"
            )

        # Check TTL
        created = datetime.fromisoformat(stored["created_at"])
        if datetime.utcnow() - created > timedelta(hours=TTL_HOURS):
            # Expired, allow reuse
            return None

        return CachedResponse(
            response=stored["response"],
            status_code=stored["status_code"],
        )

    def store(self, key: str, request_hash: str, response: dict, status_code: int) -> None:
        keys = FileStore.read_json(KEYS_PATH, default={})
        keys[key] = {
            "request_hash": request_hash,
            "response": response,
            "status_code": status_code,
            "created_at": datetime.utcnow().isoformat(),
        }
        FileStore.write_json(KEYS_PATH, keys)
