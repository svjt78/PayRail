"""Vault Service - Tokenization, encryption, key rotation, and access logging."""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import sys
sys.path.insert(0, "/app/shared")

from shared.file_store import FileStore
from shared.crypto import VaultCrypto
from shared.correlation import get_correlation_id, set_correlation_id, generate_correlation_id
from shared.middleware import CorrelationMiddleware

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("vault-service")

app = FastAPI(title="PayRail Vault Service", version="1.0.0")
app.add_middleware(CorrelationMiddleware)

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
VAULT_DIR = os.path.join(DATA_DIR, "vault")
TOKENS_PATH = os.path.join(VAULT_DIR, "tokens.json")
CARDS_PATH = os.path.join(VAULT_DIR, "encrypted_cards.json")
ACCESS_LOG_PATH = os.path.join(VAULT_DIR, "access_log.jsonl")
KEYS_PATH = os.path.join(VAULT_DIR, "keys.json")

crypto = VaultCrypto(KEYS_PATH)

# BIN table for card brand detection
BIN_BRANDS = {
    "4": "visa",
    "5": "mastercard",
    "37": "amex",
    "6": "discover",
}


def detect_brand(pan: str) -> str:
    if pan.startswith("37"):
        return "amex"
    for prefix, brand in BIN_BRANDS.items():
        if pan.startswith(prefix):
            return brand
    return "unknown"


def log_access(action: str, token: str, requester: str, purpose: str):
    FileStore.append_jsonl(ACCESS_LOG_PATH, {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "token": token,
        "requester": requester,
        "purpose": purpose,
        "correlation_id": get_correlation_id(),
    })


# === Request/Response Models ===

class TokenizeRequest(BaseModel):
    pan: str
    expiry: str
    cardholder_name: Optional[str] = None
    requester: str = "api-gateway"
    purpose: str = "payment"


class TokenizeResponse(BaseModel):
    token: str
    last_four: str
    card_brand: str


class DetokenizeRequest(BaseModel):
    token: str
    requester: str = "api-gateway"
    purpose: str = "display"


class DetokenizeResponse(BaseModel):
    token: str
    last_four: str
    card_brand: str
    expiry: str


class ChargeTokenRequest(BaseModel):
    token: str
    requester: str = "api-gateway"
    purpose: str = "charge"


class ChargeTokenResponse(BaseModel):
    pan: str
    expiry: str
    card_brand: str


class RotateKeysResponse(BaseModel):
    message: str
    total_keys: int


# === Endpoints ===

@app.post("/tokenize", response_model=TokenizeResponse)
async def tokenize(req: TokenizeRequest):
    if len(req.pan) < 13 or len(req.pan) > 19:
        raise HTTPException(status_code=400, detail="Invalid PAN length")

    token = f"tok_{uuid.uuid4().hex[:24]}"
    encrypted_pan = crypto.encrypt(req.pan)
    brand = detect_brand(req.pan)
    last_four = req.pan[-4:]

    # Store token mapping
    tokens = FileStore.read_json(TOKENS_PATH, default={})
    tokens[token] = encrypted_pan
    FileStore.write_json(TOKENS_PATH, tokens)

    # Store card metadata
    cards = FileStore.read_json(CARDS_PATH, default={})
    cards[token] = {
        "encrypted_pan": encrypted_pan,
        "bin": req.pan[:6],
        "last_four": last_four,
        "expiry": req.expiry,
        "card_brand": brand,
        "cardholder_name": req.cardholder_name,
        "created_at": datetime.utcnow().isoformat(),
    }
    FileStore.write_json(CARDS_PATH, cards)

    log_access("tokenize", token, req.requester, req.purpose)
    logger.info(f"Tokenized card ending {last_four} -> {token}")

    return TokenizeResponse(token=token, last_four=last_four, card_brand=brand)


@app.post("/detokenize", response_model=DetokenizeResponse)
async def detokenize(req: DetokenizeRequest):
    cards = FileStore.read_json(CARDS_PATH, default={})
    if req.token not in cards:
        raise HTTPException(status_code=404, detail="Token not found")

    card = cards[req.token]
    log_access("detokenize", req.token, req.requester, req.purpose)

    return DetokenizeResponse(
        token=req.token,
        last_four=card["last_four"],
        card_brand=card["card_brand"],
        expiry=card["expiry"],
    )


@app.post("/charge-token", response_model=ChargeTokenResponse)
async def charge_token(req: ChargeTokenRequest):
    tokens = FileStore.read_json(TOKENS_PATH, default={})
    cards = FileStore.read_json(CARDS_PATH, default={})

    if req.token not in tokens:
        raise HTTPException(status_code=404, detail="Token not found")

    encrypted_pan = tokens[req.token]
    pan = crypto.decrypt(encrypted_pan)
    card = cards[req.token]

    log_access("charge-token", req.token, req.requester, req.purpose)
    logger.info(f"Charged token {req.token}")

    return ChargeTokenResponse(
        pan=pan,
        expiry=card["expiry"],
        card_brand=card["card_brand"],
    )


@app.post("/rotate-keys", response_model=RotateKeysResponse)
async def rotate_keys():
    crypto.rotate_key()
    import json
    with open(KEYS_PATH, "r") as f:
        data = json.load(f)
    total = len(data["keys"])

    log_access("rotate-keys", "N/A", "admin", "key-rotation")
    logger.info(f"Key rotated. Total keys: {total}")

    return RotateKeysResponse(message="Key rotated successfully", total_keys=total)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "vault-service"}


@app.get("/access-log")
async def access_log(limit: int = 100):
    logs = FileStore.read_jsonl(ACCESS_LOG_PATH)
    return {"entries": logs[-limit:], "total": len(logs)}
