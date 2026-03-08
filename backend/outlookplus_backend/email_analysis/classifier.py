from __future__ import annotations

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

    def classify_if_needed(self, *, user_id: str, email_id: int) -> None:
        with self.db.connect() as conn:
            analysis_repo = EmailAnalysisRepositorySqlite(conn)
            if analysis_repo.get_by_email_id(user_id=user_id, email_id=email_id) is not None:
                return

            email_repo = EmailRepositorySqlite(conn)
            email = email_repo.get_email(user_id=user_id, email_id=email_id)
            if email is None:
                return

        body_prefix = (email.body_text or "")[:2000]
        prompt = self.prompt_builder.build_email_analysis_prompt(
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
        suggested_actions: list[str] = []
        source = "default"

        try:
            resp = self.gemini.generate_json(prompt=prompt)
            parsed = self.validator.validate_email_analysis(raw_text=resp.raw_text)
            category = str(parsed["category"])
            sentiment = str(parsed["sentiment"])
            summary = str(parsed["summary"])
            suggested_actions = [str(a) for a in parsed["suggestedActions"]]
            source = "gemini"
        except (GeminiError, JsonValidationError, Exception):
            # Persist deterministic fallback once.
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
