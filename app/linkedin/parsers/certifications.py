from __future__ import annotations

from typing import Any

from app.linkedin.parsers._shared import date_range
from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver) -> list[dict[str, Any]]:
    certs = resolver.of_type("identity.profile.Certification")
    return [
        {
            "name": c.get("name"),
            "issuer": c.get("authority"),
            "credential_url": c.get("url"),
            "issue_date": date_range(c)["start_date"],
        }
        for c in certs
    ]
