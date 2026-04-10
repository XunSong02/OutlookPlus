from __future__ import annotations

from datetime import datetime, timezone


def now_utc_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
