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

    This uses stdlib `urllib` to avoid extra dependencies.

    Env vars (implementation-defined):
    - GEMINI_API_KEY
    - OUTLOOKPLUS_GEMINI_MODEL (default: gemini-1.5-flash)
    - OUTLOOKPLUS_GEMINI_ENDPOINT (default: Google Generative Language API)

    If GEMINI_API_KEY is missing, this client raises GeminiError.
    """

    rate_limiter: RateLimiter
    retry_policy: RetryPolicy

    def generate_json(self, *, prompt: str) -> GeminiResponse:
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or (os.getenv("OUTLOOKPLUS_GEMINI_API_KEY") or "").strip()

        # Back-compat / resilience: some users may mistakenly paste the API key
        # into OUTLOOKPLUS_GEMINI_ENDPOINT. Only treat it as an endpoint if it
        # looks like a URL.
        raw_endpoint = (os.getenv("OUTLOOKPLUS_GEMINI_ENDPOINT") or "").strip()
        if not api_key and raw_endpoint and not raw_endpoint.lower().startswith(("http://", "https://")):
            api_key = raw_endpoint
            raw_endpoint = ""

        if not api_key:
            raise GeminiError("GEMINI_API_KEY not set")

        model = os.getenv("OUTLOOKPLUS_GEMINI_MODEL", "gemini-1.5-flash")
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

            # Extract the model text; the API returns nested candidates.
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
