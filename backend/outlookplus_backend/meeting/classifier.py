from __future__ import annotations

from dataclasses import dataclass

from outlookplus_backend.ics import IcsExtractor
from outlookplus_backend.llm import GeminiClient, GeminiError, JsonValidationError, MeetingPromptInput, PromptBuilder, StrictJsonValidator
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import AttachmentRepositorySqlite, EmailRepositorySqlite, MeetingRepositorySqlite


@dataclass(frozen=True)
class MeetingClassifier:
    db: Db
    prompt_builder: PromptBuilder
    gemini: GeminiClient
    validator: StrictJsonValidator
    ics_extractor: IcsExtractor

    def classify_if_needed(self, *, user_id: str, email_id: int) -> None:
        with self.db.connect() as conn:
            meeting_repo = MeetingRepositorySqlite(conn)
            if meeting_repo.get_status(user_id=user_id, email_id=email_id) is not None:
                return

            email_repo = EmailRepositorySqlite(conn)
            email = email_repo.get_email(user_id=user_id, email_id=email_id)
            if email is None:
                return

            attachment_repo = AttachmentRepositorySqlite(conn)
            ics_path = attachment_repo.get_first_attachment_path_by_type(
                user_id=user_id, email_id=email_id, content_type="text/calendar"
            )

        ics_fields = None
        if ics_path:
            try:
                with open(ics_path, "rb") as f:
                    ics_fields = self.ics_extractor.extract(f.read())
            except Exception:
                ics_fields = None

        body_prefix = (email.body_text or "")[:2000]
        prompt = self.prompt_builder.build_meeting_prompt(
            input=MeetingPromptInput(
                subject=email.subject,
                from_addr=email.from_addr,
                to_addrs=email.to_addrs,
                cc_addrs=email.cc_addrs,
                sent_at_utc=email.sent_at_utc,
                body_prefix=body_prefix,
                ics_method=(ics_fields.method if ics_fields else None),
                ics_summary=(ics_fields.summary if ics_fields else None),
                ics_dtstart=(ics_fields.dtstart if ics_fields else None),
                ics_dtend=(ics_fields.dtend if ics_fields else None),
                ics_organizer=(ics_fields.organizer if ics_fields else None),
                ics_location=(ics_fields.location if ics_fields else None),
            )
        )

        try:
            response = self.gemini.generate_json(prompt=prompt)
            parsed = self.validator.validate_meeting(raw_text=response.raw_text)
            meeting_related = bool(parsed["meetingRelated"])
            confidence = float(parsed["confidence"])
            rationale = str(parsed["rationale"]) if parsed.get("rationale") is not None else None
            source = "gemini"
        except (GeminiError, JsonValidationError, Exception):
            # For US2, spec does not mandate a specific fallback row; if LLM fails,
            # leave it absent so callers see defaults.
            return

        with self.db.connect() as conn:
            MeetingRepositorySqlite(conn).upsert(
                user_id=user_id,
                email_id=email_id,
                meeting_related=meeting_related,
                confidence=confidence,
                rationale=rationale,
                source=source,
            )
