# Vault Overview (Tokenization + Encryption Boundary)

This document explains what the PayRail vault does, why it exists, and how it differs from general secret managers.

---

## What the Vault Is

The vault is a **dedicated service** that stores and protects **payment card data**.  
It provides a PCI-style security boundary so the rest of the system only sees **tokens**, not raw card numbers.

---

## Core Responsibilities

### 1. Tokenization (Safe Stand-In)
- Replaces the real **PAN** (Primary Account Number) with a **token** like `tok_...`.
- The token is used everywhere else in the system.
- The real PAN never appears outside the vault.

### 2. Encryption at Rest
- The PAN is encrypted using **Fernet** before being stored.
- Encrypted data is stored in `data/vault/encrypted_cards.json`.
- Without the keys, the PAN is unreadable.

### 3. Access Control Boundary
- Only the vault can **detokenize** or **charge-token**.
- Other services must call the vault API to get PAN data.

### 4. Audit Logging
- Every access is recorded in `data/vault/access_log.jsonl`.
- Includes **who requested**, **why**, and **correlation ID**.

### 5. Key Rotation
- The vault supports rotating encryption keys.
- Old data remains decryptable while new data uses the latest key.

---

## PAN vs Token vs Encryption (Not the Same)

- **PAN**: The actual card number printed on a card.
- **Tokenization**: Replaces PAN with a random surrogate token.
- **Encryption**: Scrambles PAN into ciphertext that can be decrypted with a key.

In PayRail:
- The **token** is used in payments.
- The **PAN** is encrypted and stored only inside the vault.

---

## What Is Stored (Demo Behavior)

✅ Stored:
- Encrypted PAN
- Expiry date
- Card brand and last four

❌ Not stored:
- CVV (PCI rules prohibit storing CVV after authorization)

---

## How It’s Used in Payments

1. **Tokenize**: UI sends PAN → vault returns token.
2. **Authorize/Capture**: API gateway sends token → vault returns PAN.
3. Provider uses PAN to authorize/capture.

The rest of the system never sees the PAN.

---

## Vault vs Cloud Secret Managers

- **Vault (PayRail)** stores card data and issues tokens.
- **Secret managers (AWS SM / Azure Key Vault)** store **keys and secrets**, not card PANs.

In a real deployment, you might store the **encryption keys** in a cloud key vault,
while PayRail’s vault stores the encrypted PAN data.

---

## Where It’s Implemented

- Vault API: `backend/vault_service/main.py`
- Encryption: `backend/shared/crypto.py`
- Access logs: `data/vault/access_log.jsonl`
