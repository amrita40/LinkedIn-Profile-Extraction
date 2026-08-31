"""
Central configuration, loaded from environment variables (.env in local dev).

We deliberately authenticate with a *session cookie* (li_at) rather than
submitting username/password programmatically. LinkedIn's login form is
protected by device-fingerprinting + CAPTCHA challenges that scripted
logins trip almost immediately, whereas a cookie lifted from an already
logged-in browser session is stable for weeks and is the approach used by
essentially every LinkedIn scraping project in the wild (including the
PhantomBuster automation linked in the brief).
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Read fresh from the environment on every instantiation (not at class
    body/import time) so tests can monkeypatch env vars and get_settings()
    picks them up after a cache_clear()."""

    def __init__(self) -> None:
        # --- LinkedIn session credentials (see README "Setup") ---
        self.LI_AT: str = os.getenv("LI_AT", "")
        self.JSESSIONID: str = os.getenv("JSESSIONID", "")

        # --- API access control (protects *your* hosted endpoint, not LinkedIn's) ---
        self.API_KEY: str = os.getenv("API_KEY", "")

        # --- Caching ---
        self.CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

        # --- Rate limiting (requests per minute per API key / IP) ---
        self.RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

        # --- Networking ---
        self.REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

    @property
    def is_configured(self) -> bool:
        return bool(self.LI_AT and self.JSESSIONID)


@lru_cache
def get_settings() -> Settings:
    return Settings()
