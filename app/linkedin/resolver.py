"""
LinkedIn's Voyager responses are not flat JSON — they're a normalized
entity graph: a top-level `data` object plus an `included` array holding
every entity (positions, schools, skills, images...) referenced anywhere
in the response, each tagged with an `entityUrn` and a `$type`.

This module does the one generic, reusable piece of that: building an
entityUrn -> entity lookup and filtering entities by `$type`. Section
parsers (app/linkedin/parsers/*.py) each ask this resolver for "give me
all entities that look like a Position" and take it from there.
"""
from __future__ import annotations

from typing import Any


class EntityResolver:
    def __init__(self, raw_response: dict[str, Any]):
        self.raw = raw_response
        self.data: dict[str, Any] = raw_response.get("data", {}) or {}
        self._index: dict[str, dict[str, Any]] = {}
        for entity in raw_response.get("included", []) or []:
            urn = entity.get("entityUrn")
            if urn:
                self._index[urn] = entity

    def by_urn(self, urn: str) -> dict[str, Any] | None:
        return self._index.get(urn)

    def of_type(self, type_fragment: str) -> list[dict[str, Any]]:
        """Every included entity whose $type contains `type_fragment`,
        e.g. 'identity.profile.Position'."""
        return [e for e in self._index.values() if type_fragment in (e.get("$type") or "")]

    def profile_entity(self) -> dict[str, Any]:
        """The core profile card: the one Profile-typed entity that isn't
        the lightweight 'miniProfile' summary used elsewhere in LinkedIn's
        UI (comments, search results, etc.)."""
        for entity in self._index.values():
            t = entity.get("$type") or ""
            if "Profile" in t and "miniProfile" not in t:
                return entity
        return self.data
