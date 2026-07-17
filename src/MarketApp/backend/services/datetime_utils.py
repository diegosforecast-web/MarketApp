"""Datetime parsing utilities compatible with Python 3.10."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


_FRACTION_PATTERN = re.compile(
    r"^(?P<head>.+?\.)(?P<fraction>\d+)"
    r"(?P<timezone>Z|[+-]\d{2}:?\d{2})?$"
)


def parse_iso_datetime(value: Any) -> datetime:
    """
    Parse ISO timestamps while normalizing fractional seconds.

    Python 3.10 may reject timestamps containing fractional-second
    precision other than exactly three or six digits. Supabase can return
    values such as 2026-07-16T01:14:18.5102+00:00.
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()

        if not raw:
            raise ValueError("Datetime value is empty.")

        match = _FRACTION_PATTERN.match(raw)

        if match:
            fraction = (
                match.group("fraction")[:6].ljust(6, "0")
            )
            timezone_part = match.group("timezone") or ""
            raw = (
                f"{match.group('head')}"
                f"{fraction}{timezone_part}"
            )

        raw = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
