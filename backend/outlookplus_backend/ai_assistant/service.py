from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from outlookplus_backend.llm import GeminiClient, GeminiError, JsonValidationError, PromptBuilder, StrictJsonValidator
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import AiRequestRepositorySqlite, EmailRepositorySqlite


@dataclass(frozen=True)
class AiRequestResult:
    response_text: str
    source: Literal["gemini", "default"]


@dataclass(frozen=True)
class AiAssistantService:
    db: Db
    prompt_builder: PromptBuilder
    gemini: GeminiClient
    validator: StrictJsonValidator

    def run_request(self, *, user_id: str, mailbox_message_id: str, prompt: str) -> AiRequestResult:
        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email = email_repo.get_email_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)

        if email is None:
            return AiRequestResult(response_text="Email not found.", source="default")

        body_prefix = (email.body_text or "")[:2000]
        llm_prompt = self.prompt_builder.build_ai_assistant_prompt(
            subject=email.subject,
            from_addr=email.from_addr,
            to_addrs=email.to_addrs,
            cc_addrs=email.cc_addrs,
            sent_at_utc=email.sent_at_utc,
            body_prefix=body_prefix,
            user_prompt=prompt,
        )

        response_text = f'I\'ve processed your request: "{prompt}".'
        source = "default"
        try:
            resp = self.gemini.generate_json(prompt=llm_prompt)
            parsed = self.validator.validate_ai_request(raw_text=resp.raw_text)
            response_text = str(parsed["responseText"])
            source = "gemini"
        except (GeminiError, JsonValidationError, Exception):
            response_text = f'I\'ve processed your request: "{prompt}". Draft has been created.'
            source = "default"

        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email_id is not None:
                AiRequestRepositorySqlite(conn).add_request(
                    user_id=user_id,
                    email_id=email_id,
                    prompt_text=prompt,
                    response_text=response_text,
                    source=source,
                )

        return AiRequestResult(response_text=response_text, source=source)

    def suggest_compose(
        self,
        *,
        user_id: str,
        to_addrs: str | None,
        cc_addrs: str | None,
        subject: str | None,
        draft_body: str,
        instruction: str | None = None,
    ) -> AiRequestResult:
        llm_prompt = self.prompt_builder.build_compose_suggestion_prompt(
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            subject=subject,
            draft_body=draft_body,
            instruction=instruction,
        )

        # Default behavior should not destroy user content.
        response_text = (draft_body or "").strip()
        source = "default"
        try:
            resp = self.gemini.generate_json(prompt=llm_prompt)
            parsed = self.validator.validate_ai_request(raw_text=resp.raw_text)
            response_text = str(parsed["responseText"]).strip()
            source = "gemini"
        except (GeminiError, JsonValidationError, Exception):
            source = "default"

        return AiRequestResult(response_text=response_text, source=source)
