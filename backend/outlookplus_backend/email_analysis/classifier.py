from __future__ import annotations

import os
from dataclasses import dataclass

from outlookplus_backend.llm import GeminiClient, GeminiError, JsonValidationError, PromptBuilder, StrictJsonValidator
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailAnalysisRepositorySqlite, EmailRepositorySqlite


@dataclass(frozen=True)
class EmailAnalysisClassifier:
    db: Db
    prompt_builder: PromptBuilder
    gemini: GeminiClient
    validator: StrictJsonValidator

    def classify_if_needed(self, *, user_id: str, email_id: int, allow_persist_default: bool = True) -> None:
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or (os.getenv("OUTLOOKPLUS_GEMINI_API_KEY") or "").strip()
        raw_endpoint = (os.getenv("OUTLOOKPLUS_GEMINI_ENDPOINT") or "").strip()
        if not api_key and raw_endpoint and not raw_endpoint.lower().startswith(("http://", "https://")):
            api_key = raw_endpoint
        # Also treat user-stored credentials (injected via GeminiClient) as available.
        has_gemini = bool(api_key) or (getattr(self.gemini, "gemini_credentials", None) is not None)

        with self.db.connect() as conn:
            analysis_repo = EmailAnalysisRepositorySqlite(conn)
            existing = analysis_repo.get_by_email_id(user_id=user_id, email_id=email_id)
            # Treat source="default" as a placeholder; allow rerun to replace it.
            if existing is not None:
                if str(existing.get("source") or "") != "default":
                    return
                # If we only have a placeholder and Gemini isn't configured, nothing to do.
                if not has_gemini:
                    return
            else:
                # No analysis row yet.
                if not has_gemini and not allow_persist_default:
                    return

            email_repo = EmailRepositorySqlite(conn)
            email = email_repo.get_email(user_id=user_id, email_id=email_id)
            if email is None:
                return

        body_prefix = (email.body_text or "")[:2000]
        prompt = self.prompt_builder.build_email_analysis_prompt(
            folder=email.folder,
            subject=email.subject,
            from_addr=email.from_addr,
            to_addrs=email.to_addrs,
            cc_addrs=email.cc_addrs,
            sent_at_utc=email.sent_at_utc,
            body_prefix=body_prefix,
        )

        category = "Work"
        sentiment = "neutral"
        summary = (email.preview_text or email.subject or body_prefix).strip()[:240]
        suggested_actions: list[object] = []
        source = "default"

        try:
            resp = self.gemini.generate_json(prompt=prompt)
            parsed = self.validator.validate_email_analysis(raw_text=resp.raw_text)
            category = str(parsed["category"])
            sentiment = str(parsed["sentiment"])
            summary = str(parsed["summary"])
            suggested_actions = list(parsed["suggestedActions"])
            source = "gemini"
        except (GeminiError, JsonValidationError, Exception):
            # If Gemini fails even though it's configured, persist deterministic fallback once.
            if not allow_persist_default:
                return
            source = "default"

        with self.db.connect() as conn:
            EmailAnalysisRepositorySqlite(conn).upsert_analysis(
                user_id=user_id,
                email_id=email_id,
                category=category,
                sentiment=sentiment,
                summary=summary,
                suggested_actions=suggested_actions,
                source=source,
            )
