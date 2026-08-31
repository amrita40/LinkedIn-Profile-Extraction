from __future__ import annotations

from typing import Any, Optional

from app.linkedin.resolver import EntityResolver


def _vector_image_url(container: Optional[dict[str, Any]]) -> Optional[str]:
    if not container:
        return None
    display = container.get("displayImageReference", {}).get("vectorImage") or container.get("vectorImage")
    if not display:
        return None
    artifacts = display.get("artifacts", [])
    if not artifacts:
        return None
    best = max(artifacts, key=lambda a: a.get("width", 0))
    return display.get("rootUrl", "") + best.get("fileIdentifyingUrlPathSegment", "")


def parse(resolver: EntityResolver) -> dict[str, Any]:
    entity = resolver.profile_entity()
    return {
        "profile": _vector_image_url(entity.get("profilePicture") or entity.get("picture")),
        "background": _vector_image_url(entity.get("backgroundImage")),
    }
