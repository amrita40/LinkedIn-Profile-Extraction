from __future__ import annotations

from typing import Any

from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver) -> list[dict[str, Any]]:
    return [
        {"name": l.get("name"), "proficiency": l.get("proficiency")}
        for l in resolver.of_type("identity.profile.Language")
    ]
