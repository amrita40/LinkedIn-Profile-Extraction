"""
Logging setup. One rule kept everywhere in this codebase: never log
LI_AT, JSESSIONID, API_KEY, or any header/cookie value — see
app/linkedin/client.py for where that matters most.
"""
from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
