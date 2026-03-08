from __future__ import annotations

from dataclasses import dataclass

from outlookplus_backend.domain import EmailMessage
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailAnalysisRepositorySqlite
from outlookplus_backend.utils.mail import decode_rfc2047


_ALLOWED_CATEGORIES = {"Work", "Personal", "Finance", "Social", "Promotions", "Urgent"}
_ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}


def _fallback_summary(email: EmailMessage) -> str:
    text = (email.preview_text or "").strip()
    if text:
        return text[:240]
    text = (decode_rfc2047(email.subject or "") or "").strip()
    if text:
        return text[:240]
    body = (email.body_text or "").strip()
    if body:
        return body[:240]
    return ""


@dataclass(frozen=True)
class EmailAnalysisService:
    db: Db

    def _fallback(self, *, email: EmailMessage) -> dict[str, object]:
        return {
            "category": "Work",
            "sentiment": "neutral",
            "summary": _fallback_summary(email),
            "suggestedActions": [],
        }

    def get_for_email(self, *, user_id: str, email: EmailMessage) -> dict[str, object]:
        with self.db.connect() as conn:
            repo = EmailAnalysisRepositorySqlite(conn)
            row = repo.get_by_email_id(user_id=user_id, email_id=email.id)

        if not row:
            return self._fallback(email=email)

        category = str(row.get("category") or "Work")
        sentiment = str(row.get("sentiment") or "neutral")
        summary = str(row.get("summary") or "")
        summary = decode_rfc2047(summary) or summary
        suggested = row.get("suggestedActions")
        suggested_actions = [str(x) for x in suggested] if isinstance(suggested, list) else []

        if category not in _ALLOWED_CATEGORIES:
            category = "Work"
        if sentiment not in _ALLOWED_SENTIMENT:
            sentiment = "neutral"

        return {
            "category": category,
            "sentiment": sentiment,
            "summary": summary or _fallback_summary(email),
            "suggestedActions": suggested_actions,
        }

    def get_for_emails(self, *, user_id: str, emails: list[EmailMessage]) -> dict[int, dict[str, object]]:
        email_ids = [e.id for e in emails]
        with self.db.connect() as conn:
            repo = EmailAnalysisRepositorySqlite(conn)
            rows = repo.get_by_email_ids(user_id=user_id, email_ids=email_ids)

        out: dict[int, dict[str, object]] = {}
        for e in emails:
            row = rows.get(e.id)
            if not row:
                out[e.id] = self._fallback(email=e)
                continue

            category = str(row.get("category") or "Work")
            sentiment = str(row.get("sentiment") or "neutral")
            summary = str(row.get("summary") or "")
            summary = decode_rfc2047(summary) or summary
            suggested = row.get("suggestedActions")
            suggested_actions = [str(x) for x in suggested] if isinstance(suggested, list) else []

            if category not in _ALLOWED_CATEGORIES:
                category = "Work"
            if sentiment not in _ALLOWED_SENTIMENT:
                sentiment = "neutral"

            out[e.id] = {
                "category": category,
                "sentiment": sentiment,
                "summary": summary or _fallback_summary(e),
                "suggestedActions": suggested_actions,
            }

        return out
