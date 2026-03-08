from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass

from outlookplus_backend.llm.throttle import RateLimiter, RetryPolicy


class SmtpError(Exception):
    pass


@dataclass
class SmtpClient:
    rate_limiter: RateLimiter
    retry_policy: RetryPolicy

    def send(self, *, user_id: str, from_addr: str, to_addrs: list[str], mime_message_bytes: bytes) -> None:
        host = os.getenv("OUTLOOKPLUS_SMTP_HOST")
        username = os.getenv("OUTLOOKPLUS_SMTP_USERNAME")
        password = os.getenv("OUTLOOKPLUS_SMTP_PASSWORD")
        port = int(os.getenv("OUTLOOKPLUS_SMTP_PORT", "587"))

        if not host or not username or not password:
            raise SmtpError("SMTP env vars not set")

        if not to_addrs:
            raise SmtpError("No recipients")

        actual_from_addr = (from_addr or "").strip() or username

        def do_call() -> None:
            self.rate_limiter.wait()
            try:
                with smtplib.SMTP(host=host, port=port, timeout=30) as s:
                    s.ehlo()
                    try:
                        s.starttls()
                        s.ehlo()
                    except Exception:
                        pass
                    s.login(username, password)
                    s.sendmail(from_addr=actual_from_addr, to_addrs=to_addrs, msg=mime_message_bytes)
            except Exception as e:
                raise SmtpError(str(e))

        def is_retryable(e: Exception) -> bool:
            return isinstance(e, SmtpError)

        self.retry_policy.run(do_call, is_retryable=is_retryable)
