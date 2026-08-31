"""
Authentication for direct LinkedIn HTTP requests.

We authenticate the *exact same way the LinkedIn web app does on every page
load* — by attaching the session cookies issued when a user (us) logs in
through the normal, authorized LinkedIn login flow in a browser, once.
No password is ever handled by this code, no login form is submitted
programmatically, and no CAPTCHA/MFA/anti-abuse control is bypassed: we are
simply reusing a session LinkedIn already authenticated and issued to us.

Cookies required:
  li_at        - the main session token, issued on login (~1 year expiry)
  JSESSIONID   - a secondary session id issued alongside li_at; LinkedIn
                 also requires its (unquoted) value echoed back as the
                 `csrf-token` header on every /voyager/api/* call.

See README "Setup" for the exact click-path to retrieve these from your
own browser's dev tools after logging in.
"""
from __future__ import annotations

import httpx

from app.config import Settings


class LinkedInAuthError(Exception):
    """Session cookies are missing, expired, or LinkedIn returned a
    login/checkpoint challenge instead of API data."""


def build_authenticated_client(settings: Settings) -> httpx.Client:
    """Construct an httpx.Client pre-loaded with the session cookies and
    headers LinkedIn's own front-end sends on every Voyager API call."""
    if not settings.is_configured:
        raise LinkedInAuthError(
            "LI_AT and JSESSIONID are not configured — see README Setup."
        )

    jsessionid = settings.JSESSIONID
    if not jsessionid.startswith('"'):
        jsessionid = f'"{jsessionid}"'

    cookies = httpx.Cookies()
    cookies.set("li_at", settings.LI_AT, domain=".linkedin.com")
    cookies.set("JSESSIONID", jsessionid, domain=".linkedin.com")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-restli-protocol-version": "2.0.0",
        "x-li-lang": "en_US",
        "csrf-token": jsessionid.strip('"'),
    }

    return httpx.Client(
        base_url="https://www.linkedin.com",
        cookies=cookies,
        headers=headers,
        timeout=settings.REQUEST_TIMEOUT_SECONDS,
    )
