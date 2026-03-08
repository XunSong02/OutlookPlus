from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeetingPromptInput:
    subject: str | None
    from_addr: str | None
    to_addrs: str | None
    cc_addrs: str | None
    sent_at_utc: str | None
    body_prefix: str
    ics_method: str | None
    ics_summary: str | None
    ics_dtstart: str | None
    ics_dtend: str | None
    ics_organizer: str | None
    ics_location: str | None


@dataclass(frozen=True)
class ReplyNeedPromptInput:
    subject: str | None
    from_addr: str | None
    to_addrs: str | None
    cc_addrs: str | None
    sent_at_utc: str | None
    body_prefix: str
    meeting_related: bool
    meeting_confidence: float


class PromptBuilder:
    def build_meeting_prompt(self, *, input: MeetingPromptInput) -> str:
        # Keep prompt deterministic and bounded; ask for strict JSON only.
        return (
            "You are a classifier for email meeting-related intent.\n"
            "Return ONLY valid JSON matching this schema:\n"
            '{"meetingRelated": boolean, "confidence": number, "rationale": string}\n\n'
            "Rules:\n"
            "- confidence must be between 0.0 and 1.0\n"
            "- rationale should be brief\n\n"
            "Email:\n"
            f"subject: {input.subject!r}\n"
            f"from: {input.from_addr!r}\n"
            f"to: {input.to_addrs!r}\n"
            f"cc: {input.cc_addrs!r}\n"
            f"sentAtUtc: {input.sent_at_utc!r}\n\n"
            "bodyPrefix:\n"
            f"{input.body_prefix}\n\n"
            "ics:\n"
            f"method: {input.ics_method!r}\n"
            f"summary: {input.ics_summary!r}\n"
            f"dtstart: {input.ics_dtstart!r}\n"
            f"dtend: {input.ics_dtend!r}\n"
            f"organizer: {input.ics_organizer!r}\n"
            f"location: {input.ics_location!r}\n"
        )

    def build_reply_need_prompt(self, *, input: ReplyNeedPromptInput) -> str:
        return (
            "You are a classifier for whether an email needs a reply.\n"
            "Return ONLY valid JSON matching this schema:\n"
            '{"label": "NEEDS_REPLY"|"NO_REPLY_NEEDED"|"UNSURE", "confidence": number, "reasons": string[]}\n\n'
            "Rules:\n"
            "- confidence must be between 0.0 and 1.0\n"
            "- reasons must contain 1 to 3 short strings\n"
            "- Use UNSURE if unclear\n\n"
            "Email:\n"
            f"subject: {input.subject!r}\n"
            f"from: {input.from_addr!r}\n"
            f"to: {input.to_addrs!r}\n"
            f"cc: {input.cc_addrs!r}\n"
            f"sentAtUtc: {input.sent_at_utc!r}\n"
            f"meetingRelatedSignal: {input.meeting_related} (confidence={input.meeting_confidence})\n\n"
            "bodyPrefix:\n"
            f"{input.body_prefix}\n"
        )

    def build_email_analysis_prompt(
        self,
        *,
        subject: str | None,
        from_addr: str | None,
        to_addrs: str | None,
        cc_addrs: str | None,
        sent_at_utc: str | None,
        body_prefix: str,
    ) -> str:
        return (
            "You are a classifier for email category and sentiment, plus a brief summary and suggested actions.\n"
            "Return ONLY valid JSON matching this schema:\n"
            '{"category": "Work"|"Personal"|"Finance"|"Social"|"Promotions"|"Urgent", '
            '"sentiment": "positive"|"neutral"|"negative", "summary": string, "suggestedActions": string[]}\n\n'
            "Rules:\n"
            "- summary must be 1 to 2 sentences\n"
            "- suggestedActions must be 0 to 5 short strings\n\n"
            "Email:\n"
            f"subject: {subject!r}\n"
            f"from: {from_addr!r}\n"
            f"to: {to_addrs!r}\n"
            f"cc: {cc_addrs!r}\n"
            f"sentAtUtc: {sent_at_utc!r}\n\n"
            "bodyPrefix:\n"
            f"{body_prefix}\n"
        )

    def build_ai_assistant_prompt(
        self,
        *,
        subject: str | None,
        from_addr: str | None,
        to_addrs: str | None,
        cc_addrs: str | None,
        sent_at_utc: str | None,
        body_prefix: str,
        user_prompt: str,
    ) -> str:
        return (
            "You are an assistant helping the user act on an email.\n"
            "Return ONLY valid JSON matching this schema:\n"
            '{"responseText": string}\n\n'
            "Rules:\n"
            "- responseText should be concise and actionable\n\n"
            "Email:\n"
            f"subject: {subject!r}\n"
            f"from: {from_addr!r}\n"
            f"to: {to_addrs!r}\n"
            f"cc: {cc_addrs!r}\n"
            f"sentAtUtc: {sent_at_utc!r}\n\n"
            "bodyPrefix:\n"
            f"{body_prefix}\n\n"
            "UserRequest:\n"
            f"{user_prompt}\n"
        )

    def build_compose_suggestion_prompt(
        self,
        *,
        to_addrs: str | None,
        cc_addrs: str | None,
        subject: str | None,
        draft_body: str,
        instruction: str | None,
    ) -> str:
        # Keep prompt deterministic and bounded; ask for strict JSON only.
        draft = (draft_body or "").strip()
        if len(draft) > 4000:
            draft = draft[:4000]

        user_instruction = (instruction or "").strip()
        if not user_instruction:
            user_instruction = "Rewrite the draft to be clear, professional, and concise while preserving meaning."

        return (
            "You are a writing assistant helping the user polish an email draft.\n"
            "Return ONLY valid JSON matching this schema:\n"
            '{"responseText": string}\n\n'
            "Rules:\n"
            "- responseText must be the revised email body only (no subject line, no greeting outside the body unless appropriate)\n"
            "- Preserve the original intent and factual details\n"
            "- Keep the language consistent with the input unless the user instruction requests otherwise\n"
            "- Do not invent names, dates, or commitments\n\n"
            "Context:\n"
            f"to: {to_addrs!r}\n"
            f"cc: {cc_addrs!r}\n"
            f"subject: {subject!r}\n\n"
            "DraftBody:\n"
            f"{draft}\n\n"
            "UserInstruction:\n"
            f"{user_instruction}\n"
        )
