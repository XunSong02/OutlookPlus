from __future__ import annotations

from dataclasses import dataclass

from outlookplus_backend.config import ReplyNeedConfig
from outlookplus_backend.domain import ReplyNeedResult
from outlookplus_backend.llm import GeminiClient, GeminiError, JsonValidationError, PromptBuilder, ReplyNeedPromptInput, StrictJsonValidator
from outlookplus_backend.meeting.service import MeetingService
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailRepositorySqlite, ReplyNeedRepositorySqlite


@dataclass(frozen=True)
class ReplyNeedService:
    db: Db
    meeting_service: MeetingService
    prompt_builder: PromptBuilder
    gemini: GeminiClient
    validator: StrictJsonValidator
    config: ReplyNeedConfig

    def classify(self, *, user_id: str, mailbox_message_id: str) -> ReplyNeedResult:
        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email = email_repo.get_email_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email is None:
                # Deterministic response even when email missing.
                return ReplyNeedResult(label="UNSURE", confidence=0.0, reasons=["Email not found"], source="default")

            rn_repo = ReplyNeedRepositorySqlite(conn)
            cached = rn_repo.get(user_id=user_id, email_id=email.id)
            if cached is not None:
                _id, result = cached
                return result

        meeting = self.meeting_service.get_status(user_id=user_id, email_id=email.id)
        body_prefix = (email.body_text or "")[:2000]

        prompt = self.prompt_builder.build_reply_need_prompt(
            input=ReplyNeedPromptInput(
                subject=email.subject,
                from_addr=email.from_addr,
                to_addrs=email.to_addrs,
                cc_addrs=email.cc_addrs,
                sent_at_utc=email.sent_at_utc,
                body_prefix=body_prefix,
                meeting_related=meeting.meeting_related,
                meeting_confidence=meeting.confidence,
            )
        )

        try:
            response = self.gemini.generate_json(prompt=prompt)
            parsed = self.validator.validate_reply_need(raw_text=response.raw_text)
            label = str(parsed["label"])
            confidence = float(parsed["confidence"])
            reasons = list(parsed["reasons"])

            if confidence < self.config.min_confidence:
                raise ValueError("Below min confidence")

            result = ReplyNeedResult(label=label, confidence=confidence, reasons=reasons, source="gemini")
        except (GeminiError, JsonValidationError, Exception):
            result = ReplyNeedResult(label="UNSURE", confidence=0.0, reasons=["Unable to classify"], source="default")

        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email_id is None:
                return result
            ReplyNeedRepositorySqlite(conn).upsert(user_id=user_id, email_id=email_id, result=result)

        return result

    def submit_feedback(
        self,
        *,
        user_id: str,
        mailbox_message_id: str,
        user_label: str,
        comment: str | None,
    ) -> None:
        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email_id is None:
                return

            rn_repo = ReplyNeedRepositorySqlite(conn)
            cached = rn_repo.get(user_id=user_id, email_id=email_id)
            classification_id = cached[0] if cached is not None else None
            rn_repo.add_feedback(
                user_id=user_id,
                email_id=email_id,
                classification_id=classification_id,
                user_label=user_label,
                comment=comment,
            )
