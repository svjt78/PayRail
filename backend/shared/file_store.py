"""Atomic, concurrency-safe file operations for JSON, JSONL, and CSV."""

import json
import os
import tempfile
import csv
from filelock import FileLock
from typing import Any
from pathlib import Path


class FileStore:

    @staticmethod
    def _lock_path(file_path: str) -> str:
        return f"{file_path}.lock"

    @staticmethod
    def read_json(file_path: str, default: Any = None) -> Any:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            if not os.path.exists(file_path):
                return default if default is not None else {}
            with open(file_path, "r") as f:
                return json.load(f)

    @staticmethod
    def write_json(file_path: str, data: Any) -> None:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(file_path), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                os.replace(tmp, file_path)
            except Exception:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise

    @staticmethod
    def append_jsonl(file_path: str, record: dict) -> None:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")

    @staticmethod
    def read_jsonl(file_path: str) -> list[dict]:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            if not os.path.exists(file_path):
                return []
            records = []
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            return records

    @staticmethod
    def write_csv(file_path: str, headers: list[str], rows: list[dict]) -> None:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(file_path), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(rows)
                os.replace(tmp, file_path)
            except Exception:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise

    @staticmethod
    def read_csv(file_path: str) -> list[dict]:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            if not os.path.exists(file_path):
                return []
            with open(file_path, "r") as f:
                reader = csv.DictReader(f)
                return list(reader)

    @staticmethod
    def update_json_field(file_path: str, key: str, value: Any) -> None:
        lock = FileLock(FileStore._lock_path(file_path))
        with lock:
            data = {}
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
            data[key] = value
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(file_path), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                os.replace(tmp, file_path)
            except Exception:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
