from __future__ import annotations

from email.header import decode_header, make_header


def decode_rfc2047(value: str | None) -> str | None:
    """Decode RFC2047 'encoded-word' headers into a readable unicode string.

    Examples:
      '=?UTF-8?B?5a6J5YWo5o+Q6YaS?=' -> '安全提醒' (depending on bytes)

    For non-encoded input, this returns the original string.
    """

    if value is None:
        return None

    raw = str(value)
    if not raw:
        return value

    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return value
