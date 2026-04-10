from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass

from outlookplus_backend.llm.throttle import RateLimiter, RetryPolicy


class SmtpError(Exception):
    pass


@dataclass
class SmtpClient:
    """SMTP send adapter.

    Credentials can be supplied explicitly via ``smtp_credentials`` (a
    ``SmtpCredentials`` dataclass from ``credentials.py``).  When *None* the
    client falls back to reading the legacy ``OUTLOOKPLUS_SMTP_*`` env vars so
    existing local-dev workflows keep working unchanged.
    """

    rate_limiter: RateLimiter
    retry_policy: RetryPolicy
    smtp_credentials: object | None = None  # SmtpCredentials or None

    def _resolve_credentials(self):
        """Return (host, port, username, password) from explicit creds or env."""
        creds = self.smtp_credentials
        if creds is not None:
            return creds.host, creds.port, creds.username, creds.password

        host = os.getenv("OUTLOOKPLUS_SMTP_HOST")
        username = os.getenv("OUTLOOKPLUS_SMTP_USERNAME")
        password = os.getenv("OUTLOOKPLUS_SMTP_PASSWORD")
        port = int(os.getenv("OUTLOOKPLUS_SMTP_PORT", "587"))

        if not host or not username or not password:
            raise SmtpError("SMTP env vars not set")
        return host, port, username, password

    def get_from_addr(self) -> str | None:
        """Return the configured sender address, or None."""
        try:
            _host, _port, username, _password = self._resolve_credentials()
            return username
        except SmtpError:
            return None

    def send(self, *, user_id: str, from_addr: str, to_addrs: list[str], mime_message_bytes: bytes) -> None:
        host, port, username, password = self._resolve_credentials()

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
