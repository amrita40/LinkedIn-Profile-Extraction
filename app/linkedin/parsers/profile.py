from __future__ import annotations

from typing import Any

from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver, profile_url: str) -> dict[str, Any]:
    entity = resolver.profile_entity()
    return {
        "url": profile_url,
        "public_id": resolver.data.get("publicIdentifier") or entity.get("publicIdentifier"),
        "name": " ".join(filter(None, [entity.get("firstName"), entity.get("lastName")])) or None,
        "headline": entity.get("headline"),
        "location": entity.get("geoLocationName") or entity.get("locationName"),
        "industry": entity.get("industryName"),
        "about": entity.get("summary"),
    }
