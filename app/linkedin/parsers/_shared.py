from __future__ import annotations

from typing import Any, Optional


def format_date(d: Optional[dict[str, Any]]) -> Optional[str]:
    if not d:
        return None
    year, month = d.get("year"), d.get("month")
    if year and month:
        return f"{year:04d}-{month:02d}"
    if year:
        return str(year)
    return None


def date_range(entity: dict[str, Any]) -> dict[str, Optional[str]]:
    tr = entity.get("timePeriod") or entity.get("dateRange") or {}
    return {
        "start_date": format_date(tr.get("startDate")),
        "end_date": format_date(tr.get("endDate")),
    }
