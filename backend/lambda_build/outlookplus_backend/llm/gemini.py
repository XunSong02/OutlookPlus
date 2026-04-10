from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from outlookplus_backend.llm.throttle import RateLimiter, RetryPolicy


@dataclass(frozen=True)
class GeminiResponse:
    raw_text: str


class GeminiError(Exception):
    pass


@dataclass
class GeminiClient:
    """Minimal Gemini JSON generation client.

    Credentials can be supplied explicitly via ``gemini_credentials`` (a
    ``GeminiCredentials`` dataclass from ``credentials.py``).  When *None* the
    client falls back to reading the legacy ``GEMINI_API_KEY`` /
    ``OUTLOOKPLUS_GEMINI_*`` env vars so existing local-dev workflows keep
    working unchanged.
    """

    rate_limiter: RateLimiter
    retry_policy: RetryPolicy
    gemini_credentials: object | None = None  # GeminiCredentials or None

    def _resolve_credentials(self):
        """Return (api_key, model) from explicit creds or env."""
        creds = self.gemini_credentials
        if creds is not None:
            return creds.api_key, creds.model

        api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or (os.getenv("OUTLOOKPLUS_GEMINI_API_KEY") or "").strip()

        # Back-compat: some users paste API key into OUTLOOKPLUS_GEMINI_ENDPOINT.
        raw_endpoint = (os.getenv("OUTLOOKPLUS_GEMINI_ENDPOINT") or "").strip()
        if not api_key and raw_endpoint and not raw_endpoint.lower().startswith(("http://", "https://")):
            api_key = raw_endpoint

        if not api_key:
            raise GeminiError("GEMINI_API_KEY not set")

        model = os.getenv("OUTLOOKPLUS_GEMINI_MODEL", "gemini-1.5-flash")
        return api_key, model

    def generate_json(self, *, prompt: str) -> GeminiResponse:
        api_key, model = self._resolve_credentials()

        raw_endpoint = (os.getenv("OUTLOOKPLUS_GEMINI_ENDPOINT") or "").strip()
        endpoint = (
            raw_endpoint
            if raw_endpoint.lower().startswith(("http://", "https://"))
            else f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        )

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {"temperature": 0.0},
        }

        data = json.dumps(body).encode("utf-8")

        def do_call() -> GeminiResponse:
            self.rate_limiter.wait()
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                raise GeminiError(str(e))

            try:
                text = payload["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                raise GeminiError("Unexpected Gemini response format")
            if not isinstance(text, str):
                raise GeminiError("Unexpected Gemini text type")
            return GeminiResponse(raw_text=text.strip())

        def is_retryable(e: Exception) -> bool:
            return isinstance(e, GeminiError)

        return self.retry_policy.run(do_call, is_retryable=is_retryable)
