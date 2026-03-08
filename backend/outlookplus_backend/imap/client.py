from __future__ import annotations

import imaplib
import os
from dataclasses import dataclass
from typing import Optional

from outlookplus_backend.llm.throttle import RateLimiter, RetryPolicy


@dataclass(frozen=True)
class MailboxCursor:
    uidvalidity: int
    last_seen_uid: int


@dataclass(frozen=True)
class RawMailboxMessage:
    uidvalidity: int
    uid: int
    rfc822_bytes: bytes


class MailboxError(Exception):
    pass


class MailboxClient:
    """Thin IMAP adapter.

    Env vars (MVP/dev):
    - OUTLOOKPLUS_IMAP_HOST
    - OUTLOOKPLUS_IMAP_PORT (default 993)
    - OUTLOOKPLUS_IMAP_USERNAME
    - OUTLOOKPLUS_IMAP_PASSWORD
    - OUTLOOKPLUS_IMAP_FOLDER (default INBOX)

    Per-user credentials are not implemented here; `user_id` is kept for API shape.
    """

    def __init__(self, *, rate_limiter: RateLimiter | None = None, retry_policy: RetryPolicy | None = None):
        self._rate_limiter = rate_limiter or RateLimiter(min_interval_seconds=0.0)
        self._retry_policy = retry_policy or RetryPolicy()

    def list_new_messages(self, *, user_id: str, cursor: Optional[MailboxCursor]) -> list[RawMailboxMessage]:
        host = os.getenv("OUTLOOKPLUS_IMAP_HOST")
        username = os.getenv("OUTLOOKPLUS_IMAP_USERNAME")
        password = os.getenv("OUTLOOKPLUS_IMAP_PASSWORD")
        folder = os.getenv("OUTLOOKPLUS_IMAP_FOLDER", "INBOX")
        port = int(os.getenv("OUTLOOKPLUS_IMAP_PORT", "993"))

        if not host or not username or not password:
            raise MailboxError(
                "IMAP not configured (set OUTLOOKPLUS_IMAP_HOST/OUTLOOKPLUS_IMAP_USERNAME/OUTLOOKPLUS_IMAP_PASSWORD)"
            )

        def do_call() -> list[RawMailboxMessage]:
            self._rate_limiter.wait()
            imap = imaplib.IMAP4_SSL(host=host, port=port, timeout=30)
            try:
                caps_text = ""
                try:
                    typ, caps = imap.capability()
                    if typ == "OK" and caps:
                        # caps may be a list like [b'IMAP4rev1 ...']
                        caps_text = " ".join(
                            [c.decode("utf-8", errors="replace") if isinstance(c, (bytes, bytearray)) else str(c) for c in caps]
                        )
                except Exception:
                    caps_text = ""

                try:
                    imap.login(username, password)
                except Exception as e:
                    extra = f" (capability={caps_text})" if caps_text else ""
                    raise MailboxError(f"IMAP login failed: {e}{extra}")
                typ, data = imap.select(folder, readonly=True)
                if typ != "OK":
                    raise MailboxError(f"IMAP select failed for folder={folder!r}")

                # UIDVALIDITY
                uidvalidity = 0
                typ, resp = imap.response("UIDVALIDITY")
                if typ == "OK" and resp and resp[0]:
                    try:
                        uidvalidity = int(resp[0])
                    except Exception:
                        uidvalidity = 0

                start_uid = 1
                if cursor is not None and cursor.uidvalidity == uidvalidity:
                    start_uid = max(1, cursor.last_seen_uid + 1)

                typ, ids = imap.uid("search", None, f"UID {start_uid}:*")
                if typ != "OK":
                    raise MailboxError("IMAP UID search failed")
                if not ids or not ids[0]:
                    return []

                uid_list = [int(x) for x in ids[0].split() if x]
                out: list[RawMailboxMessage] = []
                for uid in sorted(uid_list):
                    typ, msg_data = imap.uid("fetch", str(uid), "(RFC822)")
                    if typ != "OK" or not msg_data:
                        continue
                    # msg_data is list of tuples: (b'UID ...', bytes)
                    rfc822_bytes = None
                    for item in msg_data:
                        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], (bytes, bytearray)):
                            rfc822_bytes = bytes(item[1])
                            break
                    if rfc822_bytes is None:
                        continue
                    out.append(RawMailboxMessage(uidvalidity=uidvalidity, uid=uid, rfc822_bytes=rfc822_bytes))
                return out
            finally:
                try:
                    imap.logout()
                except Exception:
                    pass

        def is_retryable(e: Exception) -> bool:
            return True

        return self._retry_policy.run(do_call, is_retryable=is_retryable)
