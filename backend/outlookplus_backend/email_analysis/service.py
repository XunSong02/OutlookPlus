from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr

from outlookplus_backend.domain import EmailMessage
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailAnalysisRepositorySqlite
from outlookplus_backend.utils.mail import decode_rfc2047


_ALLOWED_CATEGORIES = {"Work", "Personal", "Finance", "Social", "Promotions", "Urgent"}
_ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}


def _safe_sender_email(from_addr: str | None) -> str:
    decoded = decode_rfc2047(from_addr or "") or (from_addr or "")
    _name, email_addr = parseaddr(decoded)
    email_addr = (email_addr or "").strip()
    return email_addr or "unknown@example.com"


def _safe_sender_name(from_addr: str | None) -> str:
    decoded = decode_rfc2047(from_addr or "") or (from_addr or "")
    name, email_addr = parseaddr(decoded)
    name = (name or "").strip()
    email_addr = (email_addr or "").strip()
    if not name and email_addr:
        name = email_addr.split("@")[0]
    return name or "there"


def _safe_subject(subject: str | None) -> str:
    decoded = decode_rfc2047(subject or "") or (subject or "")
    return (decoded or "").strip()


def _reply_subject(subject: str | None) -> str:
    s = _safe_subject(subject)
    if not s:
        return "Re:"
    return s if s.lower().startswith("re:") else f"Re: {s}"


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        t = (x or "").strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _make_reply_draft(email: EmailMessage) -> dict[str, object]:
    name = _safe_sender_name(email.from_addr)
    to_addr = _safe_sender_email(email.from_addr)
    subj = _reply_subject(email.subject)
    brief = f"Hi {name}, thanks for your email. I’ll review and get back to you soon."
    body = f"Hi {name},\n\nThanks for your email. I’ll review and get back to you soon.\n\nBest,"
    return {
        "kind": "reply_draft",
        "text": brief,
        "draft": {"to": to_addr, "subject": subj, "body": body},
    }


def _fallback_suggestions(email: EmailMessage) -> list[dict[str, object]]:
    folder = (email.folder or "").lower()

    if folder == "drafts":
        texts = [
            "Finish the draft and send when ready.",
            "Ignore for now if waiting on inputs.",
            "Discard the draft if no longer needed.",
        ]
        return [{"kind": "suggestion", "text": t} for t in texts]

    if folder in {"sent", "trash", "spam"}:
        texts = [
            "Ignore if no further action is required.",
            "Check what happened and confirm details.",
            "Archive for reference.",
        ]
        return [{"kind": "suggestion", "text": t} for t in texts]

    # inbox + anything else
    return [
        _make_reply_draft(email),
        {"kind": "suggestion", "text": "Ignore if no action is required."},
        {"kind": "suggestion", "text": "Check what happened and confirm details."},
    ]


def _has_reply_draft(actions: list[dict[str, object]]) -> bool:
    for a in actions:
        if str(a.get("kind") or "") == "reply_draft":
            return True
    return False


def _as_action_dict(x: object) -> dict[str, object] | None:
    if not isinstance(x, dict):
        return None
    kind = str(x.get("kind") or "").strip()
    text = str(x.get("text") or "").strip()
    if kind not in {"reply_draft", "suggestion"}:
        return None
    if not text:
        return None

    if kind == "reply_draft":
        draft = x.get("draft")
        if not isinstance(draft, dict):
            return None
        to = str(draft.get("to") or "").strip()
        subject = str(draft.get("subject") or "").strip()
        body = str(draft.get("body") or "")
        if not (to and subject and body.strip()):
            return None
        return {"kind": "reply_draft", "text": text, "draft": {"to": to, "subject": subject, "body": body}}

    return {"kind": "suggestion", "text": text}


def _normalize_actions(*, email: EmailMessage, persisted: list[object]) -> list[dict[str, object]]:
    """Return only Gemini-generated actions. No fallback padding —
    the frontend shows 'AI analyzing...' until real results arrive."""
    out: list[dict[str, object]] = []

    for item in persisted:
        if len(out) >= 3:
            break
        if isinstance(item, dict):
            a = _as_action_dict(item)
            if not a:
                continue
            if str(a.get("kind") or "") == "reply_draft" and _has_reply_draft(out):
                continue
            out.append(a)
        elif isinstance(item, str):
            t = item.strip()
            if t:
                out.append({"kind": "suggestion", "text": t})

    return out[:3]


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
            "category": "",
            "sentiment": "",
            "summary": "",
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
        persisted_actions: list[object] = list(suggested) if isinstance(suggested, list) else []

        if category not in _ALLOWED_CATEGORIES:
            category = "Work"
        if sentiment not in _ALLOWED_SENTIMENT:
            sentiment = "neutral"

        suggested_actions = _normalize_actions(email=email, persisted=persisted_actions)

        return {
            "category": category,
            "sentiment": sentiment,
            "summary": summary,
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
            persisted_actions: list[object] = list(suggested) if isinstance(suggested, list) else []

            if category not in _ALLOWED_CATEGORIES:
                category = "Work"
            if sentiment not in _ALLOWED_SENTIMENT:
                sentiment = "neutral"

            suggested_actions = _normalize_actions(email=e, persisted=persisted_actions)

            out[e.id] = {
                "category": category,
                "sentiment": sentiment,
                "summary": summary or _fallback_summary(e),
                "suggestedActions": suggested_actions,
            }

        return out
