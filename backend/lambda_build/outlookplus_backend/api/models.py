from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


Folder = Literal["inbox", "sent", "drafts", "trash", "spam"]
AiCategory = Literal["Work", "Personal", "Finance", "Social", "Promotions", "Urgent"]
Sentiment = Literal["positive", "neutral", "negative"]


class SuggestedActionDraftDto(BaseModel):
    to: str
    subject: str
    body: str


class SuggestedActionDto(BaseModel):
    kind: Literal["reply_draft", "suggestion"]
    text: str
    draft: SuggestedActionDraftDto | None = None


class EmailSenderDto(BaseModel):
    name: str
    email: str
    avatar: str | None = None


class AiAnalysisDto(BaseModel):
    category: AiCategory
    sentiment: Sentiment
    summary: str
    suggestedActions: list[SuggestedActionDto]


class EmailDto(BaseModel):
    id: str
    sender: EmailSenderDto
    subject: str
    preview: str
    body: str
    date: str
    read: bool
    folder: Folder
    labels: list[str]
    aiAnalysis: AiAnalysisDto


class EmailListResponse(BaseModel):
    items: list[EmailDto]
    nextCursor: str | None


class PatchEmailRequest(BaseModel):
    read: bool | None = None


class SendEmailRequest(BaseModel):
    to: str
    cc: str | None = None
    bcc: str | None = None
    subject: str
    body: str


class SendEmailResponse(BaseModel):
    id: str
    to: str
    subject: str


class EmailActionRequest(BaseModel):
    emailId: str
    action: str


class EmailActionResponse(BaseModel):
    emailId: str
    action: str
    status: Literal["ok"]


class AiRequestRequest(BaseModel):
    emailId: str
    prompt: str


class AiRequestResponse(BaseModel):
    emailId: str
    responseText: str


class AiComposeRequest(BaseModel):
    to: str | None = None
    cc: str | None = None
    subject: str | None = None
    body: str
    instruction: str | None = None


class AiComposeResponse(BaseModel):
    revisedText: str
    source: Literal["gemini", "default"]


class AttachmentDto(BaseModel):
    id: int
    filename: str | None = None
    contentType: str
    sizeBytes: int | None = None


class MeetingStatusDto(BaseModel):
    meetingRelated: bool
    confidence: float
    rationale: str | None = None
    source: str


class EmailSummaryDto(BaseModel):
    id: int
    messageId: str
    subject: str | None = None
    fromAddr: str | None = None
    receivedAtUtc: str
    meeting: MeetingStatusDto


class LegacyEmailListResponse(BaseModel):
    items: list[EmailSummaryDto]
    nextCursor: str | None


class EmailDetailDto(BaseModel):
    id: int
    messageId: str
    subject: str | None = None
    fromAddr: str | None = None
    toAddrs: str | None = None
    ccAddrs: str | None = None
    sentAtUtc: str | None = None
    receivedAtUtc: str
    bodyText: str | None = None
    attachments: list[AttachmentDto]
    meeting: MeetingStatusDto


class MeetingCheckResponse(BaseModel):
    messageId: str
    meetingRelated: bool
    confidence: float
    rationale: str | None = None
    source: str


class ReplyNeedRequest(BaseModel):
    messageId: str


class ReplyNeedResponse(BaseModel):
    messageId: str
    label: str
    confidence: float
    reasons: list[str]
    source: str


class ReplyNeedFeedbackRequest(BaseModel):
    messageId: str
    userLabel: str
    comment: str | None = None


# ---------------------------------------------------------------------------
# Credentials management
# ---------------------------------------------------------------------------

class ImapCredentialsDto(BaseModel):
    host: str
    port: int = 993
    username: str
    password: str
    folder: str = "INBOX"


class SmtpCredentialsDto(BaseModel):
    host: str
    port: int = 587
    username: str
    password: str


class GeminiCredentialsDto(BaseModel):
    api_key: str
    model: str = "gemini-1.5-flash"


class SaveCredentialsRequest(BaseModel):
    imap: ImapCredentialsDto | None = None
    smtp: SmtpCredentialsDto | None = None
    gemini: GeminiCredentialsDto | None = None


class CredentialsStatusResponse(BaseModel):
    imap: bool
    smtp: bool
    gemini: bool


class TriggerIngestRequest(BaseModel):
    """Trigger a one-shot IMAP ingest using stored credentials."""
    pass
