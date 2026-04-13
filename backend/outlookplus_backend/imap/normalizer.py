from __future__ import annotations

from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from email.utils import parsedate_to_datetime
from datetime import timezone
from typing import Optional

from outlookplus_backend.domain import ParsedAttachment, ParsedEmail
from outlookplus_backend.utils.mail import decode_rfc2047
from outlookplus_backend.utils.time import now_utc_rfc3339


@dataclass(frozen=True)
class NormalizedMailboxMessage:
    email: ParsedEmail
    attachments: list[tuple[ParsedAttachment, bytes]]


def _header_str(msg: Message, name: str) -> Optional[str]:
    v = msg.get(name)
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return decode_rfc2047(s) or None


def _extract_body_text(msg: Message) -> Optional[str]:
    # Prefer the first text/plain part that isn't an attachment.
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/plain":
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:
                    continue
        return None

    if msg.get_content_type() == "text/plain":
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        except Exception:
            return None
    return None


def _extract_body_html(msg: Message) -> Optional[str]:
    """Extract the first text/html part that isn't an attachment."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/html":
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:
                    continue
        return None

    if msg.get_content_type() == "text/html":
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        except Exception:
            return None
    return None


def _extract_calendar_attachments(msg: Message) -> list[tuple[ParsedAttachment, bytes]]:
    out: list[tuple[ParsedAttachment, bytes]] = []
    if not msg.is_multipart():
        return out

    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        if ctype != "text/calendar":
            continue
        try:
            payload = part.get_payload(decode=True) or b""
        except Exception:
            continue
        filename = part.get_filename()
        meta = ParsedAttachment(filename=filename, content_type=ctype, size_bytes=len(payload))
        out.append((meta, payload))

    return out


def normalize_rfc822(rfc822_bytes: bytes) -> NormalizedMailboxMessage:
    msg = message_from_bytes(rfc822_bytes)

    received_at_utc = now_utc_rfc3339()
    sent_at_utc: Optional[str] = None
    date_header = _header_str(msg, "Date")
    if date_header:
        try:
            dt = parsedate_to_datetime(date_header)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            sent_at_utc = dt_utc.isoformat().replace("+00:00", "Z")
            # If we don't have a better source of receive time, use Date.
            received_at_utc = sent_at_utc
        except Exception:
            pass

    email = ParsedEmail(
        subject=_header_str(msg, "Subject"),
        from_addr=_header_str(msg, "From"),
        to_addrs=_header_str(msg, "To"),
        cc_addrs=_header_str(msg, "Cc"),
        sent_at_utc=sent_at_utc,
        received_at_utc=received_at_utc,
        body_text=_extract_body_text(msg),
        body_html=_extract_body_html(msg),
    )

    return NormalizedMailboxMessage(email=email, attachments=_extract_calendar_attachments(msg))
