# OutlookPlus API routes – all REST endpoints for the application.
from __future__ import annotations

import html
import re
import time
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from outlookplus_backend.api.models import (
    AiComposeRequest,
    AiComposeResponse,
    AiRequestRequest,
    AiRequestResponse,
    CredentialsStatusResponse,
    EmailActionRequest,
    EmailActionResponse,
    EmailDto,
    EmailListResponse,
    EmailSenderDto,
    MeetingCheckResponse,
    MeetingStatusDto,
    PatchEmailRequest,
    ReplyNeedFeedbackRequest,
    ReplyNeedRequest,
    ReplyNeedResponse,
    SaveCredentialsRequest,
    SendEmailRequest,
    SendEmailResponse,
    TriggerIngestRequest,
)
from outlookplus_backend.auth import require_user_id
from outlookplus_backend.credentials import CredentialStore
from outlookplus_backend.domain import ParsedEmail
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import AttachmentRepositorySqlite, EmailRepositorySqlite
from outlookplus_backend.smtp import SmtpError, SmtpClient
from outlookplus_backend.utils.mail import decode_rfc2047
from outlookplus_backend.utils.time import now_utc_rfc3339
from outlookplus_backend.wiring import (
    get_ai_assistant_service,
    get_credential_store,
    get_db,
    get_email_action_service,
    get_email_analysis_service,
    get_email_analysis_classifier,
    get_email_analysis_classifier_for_user,
    get_meeting_service,
    get_reply_need_service,
    get_smtp_client,
    get_smtp_for_user,
)


router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sender_from_from_addr(from_addr: str | None) -> EmailSenderDto:
    decoded = decode_rfc2047(from_addr or "") or ""
    name, email_addr = parseaddr(decoded)
    email_addr = (email_addr or "").strip()
    name = (name or "").strip()
    if not name and email_addr:
        name = email_addr.split("@")[0]
    if not name:
        name = "Unknown"
    if not email_addr:
        email_addr = "unknown@example.com"
    return EmailSenderDto(name=name, email=email_addr, avatar=None)


_URL_RE = re.compile(r'https?://[^\s<>]+')
_ANGLE_URL_RE = re.compile(r'<(https?://[^\s<>]+)>')


def _body_to_html(body_text: str | None) -> str:
    text = (body_text or "").strip()
    if not text:
        return ""
    # First, remove angle-bracket wrappers: <https://...> → https://...
    text = _ANGLE_URL_RE.sub(r'\1', text)
    # Split text into URL and non-URL segments, escape only non-URL parts
    parts: list[str] = []
    last_end = 0
    for m in _URL_RE.finditer(text):
        # Escape text before this URL
        if m.start() > last_end:
            parts.append(html.escape(text[last_end:m.start()]))
        url = m.group(0)
        display = html.escape(url)
        parts.append(f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{display}</a>')
        last_end = m.end()
    # Escape remaining text after last URL
    if last_end < len(text):
        parts.append(html.escape(text[last_end:]))
    result = "".join(parts)
    result = result.replace("\n\n", "</p><p>").replace("\n", "<br/>")
    return f"<p>{result}</p>"


def _parse_recipients(value: str | None) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    addrs = []
    for _name, addr in getaddresses([raw]):
        addr = (addr or "").strip()
        if addr:
            addrs.append(addr)
    # de-dupe while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for a in addrs:
        if a.lower() in seen:
            continue
        seen.add(a.lower())
        result.append(a)
    return result


# ---------------------------------------------------------------------------
# Credential management endpoints
# ---------------------------------------------------------------------------

@router.get("/credentials/status", response_model=CredentialsStatusResponse)
def credentials_status(
    user_id: str = Depends(require_user_id),
    store: CredentialStore = Depends(get_credential_store),
) -> CredentialsStatusResponse:
    """Check which credential types are configured (DB-stored or env-var)."""
    status = store.get_status(user_id=user_id)
    return CredentialsStatusResponse(**status)


@router.post("/credentials", response_model=CredentialsStatusResponse)
def save_credentials(
    body: SaveCredentialsRequest,
    user_id: str = Depends(require_user_id),
    store: CredentialStore = Depends(get_credential_store),
) -> CredentialsStatusResponse:
    """Save one or more credential sets (IMAP / SMTP / Gemini)."""
    if body.imap is not None:
        store.save(user_id=user_id, cred_type="imap", payload=body.imap.model_dump())
    if body.smtp is not None:
        store.save(user_id=user_id, cred_type="smtp", payload=body.smtp.model_dump())
    if body.gemini is not None:
        store.save(user_id=user_id, cred_type="gemini", payload=body.gemini.model_dump())

    status = store.get_status(user_id=user_id)
    return CredentialsStatusResponse(**status)


@router.delete("/credentials")
def delete_credentials(
    cred_type: str | None = Query(default=None),
    user_id: str = Depends(require_user_id),
    store: CredentialStore = Depends(get_credential_store),
) -> Response:
    """Delete credentials.  Pass ?cred_type=imap|smtp|gemini or omit to clear all."""
    store.delete(user_id=user_id, cred_type=cred_type)
    return Response(status_code=204)


@router.post("/ingest")
def trigger_ingest(
    user_id: str = Depends(require_user_id),
    store: CredentialStore = Depends(get_credential_store),
) -> dict:
    """Trigger a one-shot email ingest using stored/env IMAP credentials."""
    from outlookplus_backend.wiring import build_worker_for_user

    imap_creds = store.get_imap(user_id=user_id)
    if imap_creds is None:
        raise HTTPException(status_code=400, detail="IMAP credentials not configured")

    try:
        worker = build_worker_for_user(user_id=user_id)
        ingested = worker.run_once(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ingest failed: {str(e)}")

    return {"ingested": ingested}


# ---------------------------------------------------------------------------
# Email endpoints
# ---------------------------------------------------------------------------

@router.get("/emails", response_model=EmailListResponse)
def list_emails(
    folder: str = Query(default="inbox"),
    label: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None, alias="cursor"),
    user_id: str = Depends(require_user_id),
    db: Db = Depends(get_db),
    analysis_service=Depends(get_email_analysis_service),
) -> EmailListResponse:
    with db.connect() as conn:
        repo = EmailRepositorySqlite(conn)
        emails = repo.list_emails(
            user_id=user_id,
            folder=folder,
            label=label,
            limit=limit,
            cursor_received_at_utc=cursor,
        )

    analysis_by_id = analysis_service.get_for_emails(user_id=user_id, emails=emails)

    items: list[EmailDto] = []
    for e in emails:
        ai = analysis_by_id.get(e.id) or {
            "category": "Work",
            "sentiment": "neutral",
            "summary": "",
            "suggestedActions": [
                {
                    "kind": "suggestion",
                    "text": "Ignore if no action is required.",
                    "draft": None,
                },
                {
                    "kind": "suggestion",
                    "text": "Check what happened and confirm details.",
                    "draft": None,
                },
                {
                    "kind": "suggestion",
                    "text": "Archive for reference.",
                    "draft": None,
                },
            ],
        }
        items.append(
            EmailDto(
                id=e.mailbox_message_id,
                sender=_sender_from_from_addr(e.from_addr),
                subject=decode_rfc2047(e.subject or "") or "",
                preview=(e.preview_text or ""),
                body="",
                date=e.received_at_utc,
                read=bool(e.is_read),
                folder=e.folder,  # type: ignore[arg-type]
                labels=list(e.labels),
                aiAnalysis=ai,  # type: ignore[arg-type]
            )
        )

    next_cursor = emails[-1].received_at_utc if len(emails) == limit else None
    return EmailListResponse(items=items, nextCursor=next_cursor)


def get_email(
    *,
    email_id: str,
    user_id: str,
    db: Db,
    analysis_service,
    analysis_classifier=None,
) -> EmailDto:
    with db.connect() as conn:
        email_repo = EmailRepositorySqlite(conn)
        email = email_repo.get_email_by_message_id(user_id=user_id, mailbox_message_id=email_id)
        if email is None:
            raise HTTPException(status_code=404, detail="Email not found")

    if analysis_classifier is not None:
        analysis_classifier.classify_if_needed(user_id=user_id, email_id=email.id, allow_persist_default=False)

    ai = analysis_service.get_for_email(user_id=user_id, email=email)
    body = email.body_html or _body_to_html(email.body_text)
    return EmailDto(
        id=email.mailbox_message_id,
        sender=_sender_from_from_addr(email.from_addr),
        subject=decode_rfc2047(email.subject or "") or "",
        preview=(email.preview_text or ""),
        body=body,
        date=email.received_at_utc,
        read=bool(email.is_read),
        folder=email.folder,  # type: ignore[arg-type]
        labels=list(email.labels),
        aiAnalysis=ai,  # type: ignore[arg-type]
    )


@router.get("/emails/{email_id}", response_model=EmailDto)
def get_email_route(
    email_id: str,
    user_id: str = Depends(require_user_id),
    db: Db = Depends(get_db),
    analysis_service=Depends(get_email_analysis_service),
) -> EmailDto:
    # Use the user's stored Gemini credentials for lazy AI analysis.
    classifier = get_email_analysis_classifier_for_user(user_id)
    return get_email(
        email_id=email_id,
        user_id=user_id,
        db=db,
        analysis_service=analysis_service,
        analysis_classifier=classifier,
    )


@router.patch("/emails/{email_id}")
def patch_email(
    email_id: str,
    body: PatchEmailRequest,
    user_id: str = Depends(require_user_id),
    db: Db = Depends(get_db),
) -> Response:
    if body.read is None:
        raise HTTPException(status_code=400, detail="No patch fields provided")

    with db.connect() as conn:
        repo = EmailRepositorySqlite(conn)
        ok = repo.set_read(user_id=user_id, mailbox_message_id=email_id, read=bool(body.read))
    if not ok:
        raise HTTPException(status_code=404, detail="Email not found")
    return Response(status_code=204)


@router.post("/send-email", response_model=SendEmailResponse)
def send_email(
    body: SendEmailRequest,
    user_id: str = Depends(require_user_id),
    db: Db = Depends(get_db),
    store: CredentialStore = Depends(get_credential_store),
) -> SendEmailResponse:
    to_addrs = _parse_recipients(body.to)
    cc_addrs = _parse_recipients(body.cc)
    bcc_addrs = _parse_recipients(body.bcc)
    recipients = [*to_addrs, *cc_addrs, *bcc_addrs]

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients")

    # Resolve SMTP client with user's stored credentials (falls back to env).
    smtp = get_smtp_for_user(user_id)
    from_addr = smtp.get_from_addr()
    if from_addr is None:
        raise HTTPException(
            status_code=400,
            detail="SMTP not configured – set credentials in Settings or backend .env",
        )

    msg = EmailMessage()
    msg["Subject"] = body.subject
    msg["From"] = from_addr
    if to_addrs:
        msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)
    msg.set_content(body.body or "")

    try:
        smtp.send(user_id=user_id, from_addr=from_addr, to_addrs=recipients, mime_message_bytes=msg.as_bytes())
    except SmtpError as e:
        raise HTTPException(status_code=502, detail=f"SMTP send failed: {str(e)}")

    now = now_utc_rfc3339()
    mailbox_message_id = f"sent_{int(time.time() * 1000)}"

    parsed = ParsedEmail(
        subject=body.subject,
        from_addr=from_addr,
        to_addrs=body.to,
        cc_addrs=body.cc,
        sent_at_utc=now,
        received_at_utc=now,
        body_text=body.body,
    )
    preview = (body.body or "").strip()[:160]

    with db.connect() as conn:
        EmailRepositorySqlite(conn).upsert_email(
            user_id=user_id,
            mailbox_message_id=mailbox_message_id,
            email=parsed,
            folder="sent",
            is_read=True,
            labels=[],
            preview_text=preview,
            body_html=body.body,
        )

    return SendEmailResponse(id=mailbox_message_id, to=body.to, subject=body.subject)


@router.post("/email-actions", response_model=EmailActionResponse)
def email_actions(
    body: EmailActionRequest,
    user_id: str = Depends(require_user_id),
    svc=Depends(get_email_action_service),
) -> EmailActionResponse:
    try:
        svc.execute(user_id=user_id, mailbox_message_id=body.emailId, action=body.action)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email not found")

    return EmailActionResponse(emailId=body.emailId, action=body.action, status="ok")


@router.post("/ai/request", response_model=AiRequestResponse)
def ai_request(
    body: AiRequestRequest,
    user_id: str = Depends(require_user_id),
    svc=Depends(get_ai_assistant_service),
) -> AiRequestResponse:
    result = svc.run_request(user_id=user_id, mailbox_message_id=body.emailId, prompt=body.prompt)
    return AiRequestResponse(emailId=body.emailId, responseText=result.response_text)


@router.post("/ai/compose", response_model=AiComposeResponse)
def ai_compose(
    body: AiComposeRequest,
    user_id: str = Depends(require_user_id),
    svc=Depends(get_ai_assistant_service),
) -> AiComposeResponse:
    draft = (body.body or "").strip()
    if not draft:
        raise HTTPException(status_code=400, detail="Body is required")

    result = svc.suggest_compose(
        user_id=user_id,
        to_addrs=body.to,
        cc_addrs=body.cc,
        subject=body.subject,
        draft_body=draft,
        instruction=body.instruction,
    )

    return AiComposeResponse(revisedText=result.response_text, source=result.source)


@router.get("/meeting/check", response_model=MeetingCheckResponse)
def meeting_check(
    messageId: str,
    user_id: str = Depends(require_user_id),
    db: Db = Depends(get_db),
    meeting_service=Depends(get_meeting_service),
) -> MeetingCheckResponse:
    with db.connect() as conn:
        email_repo = EmailRepositorySqlite(conn)
        email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=messageId)
        if email_id is None:
            raise HTTPException(status_code=404, detail="Email not found")

    status = meeting_service.get_status(user_id=user_id, email_id=email_id)
    return MeetingCheckResponse(
        messageId=messageId,
        meetingRelated=status.meeting_related,
        confidence=status.confidence,
        rationale=status.rationale,
        source=status.source,
    )


@router.post("/reply-need", response_model=ReplyNeedResponse)
def reply_need(
    body: ReplyNeedRequest,
    user_id: str = Depends(require_user_id),
    svc=Depends(get_reply_need_service),
) -> ReplyNeedResponse:
    result = svc.classify(user_id=user_id, mailbox_message_id=body.messageId)
    return ReplyNeedResponse(
        messageId=body.messageId,
        label=result.label,
        confidence=result.confidence,
        reasons=result.reasons,
        source=result.source,
    )


@router.post("/reply-need/feedback")
def reply_need_feedback(
    body: ReplyNeedFeedbackRequest,
    user_id: str = Depends(require_user_id),
    svc=Depends(get_reply_need_service),
) -> Response:
    if body.userLabel not in {"NEEDS_REPLY", "NO_REPLY_NEEDED"}:
        raise HTTPException(status_code=400, detail="Invalid userLabel")
    svc.submit_feedback(
        user_id=user_id,
        mailbox_message_id=body.messageId,
        user_label=body.userLabel,
        comment=body.comment,
    )
    return Response(status_code=204)
