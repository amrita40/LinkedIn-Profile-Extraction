from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.cache import TTLCache
from app.config import Settings
from app.linkedin.auth import LinkedInAuthError
from app.linkedin.client import LinkedInClient, LinkedInNotFoundError, LinkedInRateLimitedError, LinkedInUpstreamError
from app.linkedin.parsers import certifications as certifications_parser
from app.linkedin.parsers import education as education_parser
from app.linkedin.parsers import experience as experience_parser
from app.linkedin.parsers import images as images_parser
from app.linkedin.parsers import languages as languages_parser
from app.linkedin.parsers import profile as profile_parser
from app.linkedin.parsers import skills as skills_parser
from app.linkedin.resolver import EntityResolver
from app.services.validation import InvalidLinkedInUrlError, canonical_profile_url, extract_public_id


class ProfileServiceError(Exception):
    """Base class carrying an API error `code` + human `message`, mapped
    to an HTTP status by the API layer (app/api/routes.py)."""

    def __init__(self, code: str, message: str, http_status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _wrap(code: str, http_status: int):
    def _raise(message: str):
        raise ProfileServiceError(code, message, http_status)
    return _raise


OPTIONAL_SECTIONS = ("experience", "education", "skills", "certifications", "languages")


class ProfileService:
    def __init__(self, settings: Settings, cache: TTLCache):
        self.settings = settings
        self.cache = cache

    def get_profile(self, raw_url: str, include_contact_info: bool = False) -> dict[str, Any]:
        try:
            public_id = extract_public_id(raw_url)
        except InvalidLinkedInUrlError as exc:
            raise ProfileServiceError("INVALID_LINKEDIN_URL", str(exc), 400)

        cache_key = f"{public_id}:{include_contact_info}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached = {**cached}
            cached["metadata"] = {**cached["metadata"], "cached": True, "status": "cached"}
            return cached

        if not self.settings.is_configured:
            raise ProfileServiceError(
                "SERVICE_NOT_CONFIGURED",
                "Server is missing LI_AT/JSESSIONID configuration — see README Setup.",
                503,
            )

        result = self._fetch_and_normalize(public_id, include_contact_info)
        self.cache.set(cache_key, result)
        return result

    def _fetch_and_normalize(self, public_id: str, include_contact_info: bool) -> dict[str, Any]:
        try:
            with LinkedInClient(self.settings) as client:
                raw = client.get_profile(public_id)
                contact_raw = client.get_contact_info(public_id) if include_contact_info else None
        except LinkedInAuthError as exc:
            raise ProfileServiceError("UNAUTHORIZED_OR_FORBIDDEN", str(exc), 401)
        except LinkedInNotFoundError as exc:
            raise ProfileServiceError("PROFILE_NOT_FOUND", str(exc), 404)
        except LinkedInRateLimitedError as exc:
            raise ProfileServiceError("UPSTREAM_RATE_LIMITED", str(exc), 429)
        except LinkedInUpstreamError as exc:
            raise ProfileServiceError("LINKEDIN_UPSTREAM_ERROR", str(exc), 502)

        resolver = EntityResolver(raw)
        profile_url = canonical_profile_url(public_id)

        data = {
            "profile": profile_parser.parse(resolver, profile_url),
            "images": images_parser.parse(resolver),
            "experience": experience_parser.parse(resolver),
            "education": education_parser.parse(resolver),
            "skills": skills_parser.parse(resolver),
            "certifications": certifications_parser.parse(resolver),
            "languages": languages_parser.parse(resolver),
            "contact_info": _parse_contact_info(contact_raw) if contact_raw else None,
        }

        missing = [section for section in OPTIONAL_SECTIONS if not data[section]]
        status = "partial" if missing else "complete"

        return {
            "success": True,
            "data": data,
            "metadata": {
                "source": "linkedin",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "missing_sections": missing,
                "cached": False,
            },
        }


def _parse_contact_info(contact_raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": contact_raw.get("emailAddress"),
        "phone_numbers": [p.get("number") for p in contact_raw.get("phoneNumbers", []) if p.get("number")],
        "websites": [w.get("url") for w in contact_raw.get("websites", []) if w.get("url")],
    }
