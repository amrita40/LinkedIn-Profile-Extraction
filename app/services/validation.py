"""
Phase 8: URL validation.

Only accepts https://www.linkedin.com/in/<slug>/ (and minor variants —
missing scheme, missing www, trailing query params). Anything else is
rejected before we ever touch the network.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


class InvalidLinkedInUrlError(ValueError):
    pass


_SLUG_RE = re.compile(r"^[a-zA-Z0-9\-_%]+$")


def extract_public_id(raw_url: str) -> str:
    raw_url = (raw_url or "").strip()
    if not raw_url:
        raise InvalidLinkedInUrlError("URL is empty.")

    if "linkedin.com" not in raw_url:
        raise InvalidLinkedInUrlError(f"Not a linkedin.com URL: {raw_url!r}")

    normalized = raw_url if raw_url.startswith("http") else f"https://{raw_url}"
    parsed = urlparse(normalized)

    if not parsed.netloc.endswith("linkedin.com"):
        raise InvalidLinkedInUrlError(f"Unsupported domain: {parsed.netloc!r}")

    match = re.search(r"/in/([^/]+)/?", parsed.path)
    if not match:
        raise InvalidLinkedInUrlError(
            f"Expected a personal profile URL like https://www.linkedin.com/in/<slug>/, got: {raw_url!r}"
        )

    slug = match.group(1)
    if not _SLUG_RE.fullmatch(slug):
        raise InvalidLinkedInUrlError(f"Profile slug contains unexpected characters: {slug!r}")

    return slug


def canonical_profile_url(public_id: str) -> str:
    return f"https://www.linkedin.com/in/{public_id}/"
