"""Fernet encryption with key rotation support via MultiFernet."""

import json
import os
from cryptography.fernet import Fernet, MultiFernet


class VaultCrypto:

    def __init__(self, keys_path: str):
        self.keys_path = keys_path
        self._ensure_keys()

    def _ensure_keys(self):
        if not os.path.exists(self.keys_path):
            key = Fernet.generate_key().decode()
            os.makedirs(os.path.dirname(self.keys_path), exist_ok=True)
            with open(self.keys_path, "w") as f:
                json.dump({"keys": [key], "active_key_index": 0}, f, indent=2)

    def _load_keys(self) -> list[str]:
        with open(self.keys_path, "r") as f:
            data = json.load(f)
        return data["keys"]

    def _get_multi_fernet(self) -> MultiFernet:
        keys = self._load_keys()
        fernet_keys = [Fernet(k.encode()) for k in keys]
        return MultiFernet(fernet_keys)

    def encrypt(self, plaintext: str) -> str:
        mf = self._get_multi_fernet()
        return mf.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        mf = self._get_multi_fernet()
        return mf.decrypt(ciphertext.encode()).decode()

    def rotate_key(self) -> str:
        new_key = Fernet.generate_key().decode()
        with open(self.keys_path, "r") as f:
            data = json.load(f)
        data["keys"].insert(0, new_key)
        data["active_key_index"] = 0
        with open(self.keys_path, "w") as f:
            json.dump(data, f, indent=2)
        return new_key
