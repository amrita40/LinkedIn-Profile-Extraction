from __future__ import annotations

from app.linkedin.resolver import EntityResolver


def parse(resolver: EntityResolver) -> list[str]:
    return [s["name"] for s in resolver.of_type("identity.profile.Skill") if s.get("name")]
