from __future__ import annotations

from typing import Any

from app.linkedin.parsers._shared import date_range
from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver) -> list[dict[str, Any]]:
    positions = resolver.of_type("identity.profile.Position")
    positions.sort(
        key=lambda e: (e.get("timePeriod", {}).get("startDate", {}).get("year") or 0),
        reverse=True,
    )
    return [
        {
            "title": p.get("title"),
            "company": p.get("companyName"),
            "company_url": p.get("companyUrn"),
            "location": p.get("locationName"),
            "employment_type": p.get("employmentType"),
            "description": p.get("description"),
            **date_range(p),
        }
        for p in positions
    ]
