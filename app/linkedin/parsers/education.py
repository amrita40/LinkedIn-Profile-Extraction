from __future__ import annotations

from typing import Any

from app.linkedin.parsers._shared import date_range
from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver) -> list[dict[str, Any]]:
    educations = resolver.of_type("identity.profile.Education")
    return [
        {
            "institution": e.get("schoolName"),
            "degree": e.get("degreeName"),
            "field_of_study": e.get("fieldOfStudy"),
            "grade": e.get("grade"),
            "description": e.get("description"),
            **date_range(e),
        }
        for e in educations
    ]
