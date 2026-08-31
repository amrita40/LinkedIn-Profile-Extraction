"""
A tiny in-memory TTL cache.

Why cache at all: every request to this API costs a real request against
LinkedIn's session (which can get throttled or flagged), so re-scraping the
same profile within a short window is both wasteful and risky. Keyed by
public_id, values expire after settings.CACHE_TTL_SECONDS.

This is process-local (fine for a single instance / demo deployment). If
you scale to multiple instances, swap this for Redis — the interface below
is deliberately small so that's a drop-in change (see README "Known
limitations").
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self.ttl_seconds, value)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"entries": len(self._store)}
