# Vault Overview (Tokenization + Encryption Boundary)

This document explains what the PayRail vault does, how PAN tokenization/encryption works, and how Fernet/MultiFernet are used for key management.

## What the Vault Is

The vault is a **dedicated service** that stores and protects **payment card data**. It provides a PCI-style security boundary so the rest of the system only sees **tokens**, not raw card numbers.

## Core Responsibilities

1. **Tokenization (Safe Stand-In)**
- Replaces the real **PAN** (Primary Account Number) with a **token** like `tok_...`.
- The token is used everywhere else in the system.
- The real PAN never appears outside the vault.

2. **Encryption at Rest**
- The PAN is encrypted using **Fernet** before being stored.
- Encrypted data is stored in `data/vault/encrypted_cards.json`.
- Without the keys, the PAN is unreadable.

3. **Access Control Boundary**
- Only the vault can **detokenize** or **charge-token**.
- Other services must call the vault API to get PAN data.

4. **Audit Logging**
- Every access is recorded in `data/vault/access_log.jsonl`.
- Includes **who requested**, **why**, and **correlation ID**.

5. **Key Rotation**
- The vault supports rotating encryption keys.
- Old data remains decryptable while new data uses the latest key.

## PAN vs Token vs Encryption (Not the Same)

- **PAN**: The actual card number printed on a card.
- **Tokenization**: Replaces PAN with a random surrogate token.
- **Encryption**: Scrambles PAN into ciphertext that can be decrypted with a key.

In PayRail:
- The **token** is used in payments.
- The **PAN** is encrypted and stored only inside the vault.

## What Is Stored (Demo Behavior)

✅ Stored:
- Encrypted PAN
- Expiry date
- Card brand and last four

❌ Not stored:
- CVV (PCI rules prohibit storing CVV after authorization)

## How It’s Used in Payments

1. **Tokenize**: UI sends PAN → vault returns token.
2. **Authorize/Capture**: API gateway sends token → vault returns PAN.
3. Provider uses PAN to authorize/capture.

The rest of the system never sees the PAN.

## Vault vs Cloud Secret Managers

- **Vault (PayRail)** stores card data and issues tokens.
- **Secret managers (AWS SM / Azure Key Vault)** store **keys and secrets**, not card PANs.

In a real deployment, you might store the **encryption keys** in a cloud key vault, while PayRail’s vault stores the encrypted PAN data.

## VaultCrypto + Fernet/MultiFernet

### Scope

- Code: `backend/shared/crypto.py`
- Vault usage: `backend/vault_service/main.py`
- Key storage: `data/vault/keys.json`

### VaultCrypto (PayRail Wrapper)

`VaultCrypto` is a small wrapper around `cryptography.fernet.Fernet` and `MultiFernet`. It adds key file management and rotation, and exposes `encrypt`, `decrypt`, and `rotate_key`.

#### Responsibilities

1. **Key bootstrap**
- On initialization, `_ensure_keys()` guarantees that `data/vault/keys.json` exists.
- If missing, it generates a new Fernet key and writes:
  - `{"keys": ["<base64-key>"], "active_key_index": 0}`

2. **Key loading**
- `_load_keys()` reads the `keys` array from `data/vault/keys.json`.

3. **MultiFernet construction**
- `_get_multi_fernet()` builds one `Fernet` instance per key and wraps them in `MultiFernet`.

4. **Encryption**
- `encrypt(plaintext)` uses `MultiFernet.encrypt()` and returns base64 ciphertext.

5. **Decryption**
- `decrypt(ciphertext)` uses `MultiFernet.decrypt()` and returns plaintext.

6. **Key rotation**
- `rotate_key()` generates a new key and inserts it at index 0 of the `keys` array.
- Old keys remain so previously encrypted data remains decryptable.
- `active_key_index` is updated to `0` (note: this index is not referenced elsewhere).

### Fernet vs MultiFernet (How It Works Here)

- **Fernet** is the symmetric encryption primitive used for PAN encryption.
  - The same key is used for encrypting and decrypting.
  - Ciphertext is authenticated (tamper-evident).

- **MultiFernet** wraps multiple Fernet keys to enable rotation.
  - **Encrypt** uses the first key in the list.
  - **Decrypt** tries keys in order until one succeeds.
  - This enables key rotation without re-encrypting all data.

### Rotation Flow (API-Level)

Key rotation is triggered through the vault service endpoint:

- `POST /rotate-keys` in `backend/vault_service/main.py` calls `VaultCrypto.rotate_key()`.
- The new key becomes the first key in `data/vault/keys.json`.
- **New encryptions** use the newest key; **decryptions** try keys in order until one succeeds.
- Existing data is **not re-encrypted** during rotation.

## Vault Usage (Where Encryption Happens)

`backend/vault_service/main.py` uses `VaultCrypto` in two paths:

1. **Tokenize** (`POST /tokenize`)
- Encrypts PAN via `crypto.encrypt(pan)`.
- Stores encrypted PAN in:
  - `data/vault/tokens.json` (token -> encrypted PAN)
  - `data/vault/encrypted_cards.json` (metadata + encrypted PAN)

2. **Charge Token** (`POST /charge-token`)
- Reads encrypted PAN from `tokens.json`.
- Decrypts PAN via `crypto.decrypt(ciphertext)`.

`POST /detokenize` does not decrypt PAN; it only returns metadata.

## Key Storage

- Keys are stored in `data/vault/keys.json`.
- No key is ever passed over HTTP. The vault service manages keys internally.
- `.env` includes `VAULT_MASTER_KEY`, but it is not referenced in code.

## Notes and Constraints

- Rotation is append-only (new key inserted at the front).
- Old encrypted PANs remain decryptable as long as their key remains in `keys.json`.
- `active_key_index` is written but not used.

## Where It’s Implemented

- Vault API: `backend/vault_service/main.py`
- Encryption: `backend/shared/crypto.py`
- Access logs: `data/vault/access_log.jsonl`
