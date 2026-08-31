"""
Direct HTTP client for LinkedIn's Voyager API. No browser, no rendering —
just authenticated httpx requests, exactly reproducing what a real browser
sends (see app/linkedin/auth.py and app/linkedin/endpoints.py).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.config import Settings
from app.linkedin.auth import LinkedInAuthError, build_authenticated_client
from app.linkedin.endpoints import contact_info_url, profile_view_url

logger = logging.getLogger("linkedin_client")

# Retries only apply to transient upstream failures (timeouts, 5xx) — never
# to 401/403/404/429, which are meaningful signals (bad session, missing
# profile, real rate limit) that a retry would just mask or worsen.
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 0.5


class LinkedInNotFoundError(Exception):
    """The profile URL doesn't resolve to a real, visible profile."""


class LinkedInRateLimitedError(Exception):
    """LinkedIn itself throttled or blocked this session."""


class LinkedInUpstreamError(Exception):
    """LinkedIn returned an unexpected status/shape we can't recover from."""


class LinkedInClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.Client = build_authenticated_client(settings)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LinkedInClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str) -> dict[str, Any]:
        resp = self._get_with_retry(path)

        if resp.status_code in (401, 403):
            raise LinkedInAuthError(
                "LinkedIn rejected the session (expired cookies, or a login "
                "checkpoint was triggered). Refresh LI_AT/JSESSIONID — see README."
            )
        if resp.status_code == 404:
            raise LinkedInNotFoundError("Profile not found or not visible to this account.")
        if resp.status_code == 429:
            raise LinkedInRateLimitedError("LinkedIn is rate-limiting this session. Back off and retry later.")
        if resp.status_code >= 400:
            raise LinkedInUpstreamError(f"LinkedIn returned HTTP {resp.status_code} for {path}")

        try:
            return resp.json()
        except ValueError as exc:
            # Almost always means we got an HTML login/checkpoint page back
            # instead of JSON — i.e. the session is stale.
            raise LinkedInAuthError(
                "LinkedIn returned a non-JSON response — the session cookie is probably stale."
            ) from exc

    def _get_with_retry(self, path: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self._client.get(path)
            except httpx.TimeoutException as exc:
                last_exc = exc
            except httpx.HTTPError as exc:
                # Never log headers/cookies — they contain the session token.
                logger.warning("Network error calling LinkedIn path=%s error=%s attempt=%d", path, exc.__class__.__name__, attempt)
                last_exc = exc
            else:
                if resp.status_code >= 500 and attempt < _MAX_RETRIES:
                    logger.info("LinkedIn returned %d for path=%s, retrying (attempt %d)", resp.status_code, path, attempt + 1)
                    time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                return resp

            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))

        raise LinkedInUpstreamError(f"Failed calling LinkedIn after {_MAX_RETRIES + 1} attempts: {path}") from last_exc

    def get_profile(self, public_id: str) -> dict[str, Any]:
        """The primary, bundled response: profile core + experience +
        education + skills + certifications + languages + images."""
        return self._get(profile_view_url(public_id))

    def get_contact_info(self, public_id: str) -> Optional[dict[str, Any]]:
        """Optional second call — frequently privacy-restricted, so a
        failure here is not fatal to the overall request."""
        try:
            return self._get(contact_info_url(public_id))
        except (LinkedInNotFoundError, LinkedInAuthError):
            return None
