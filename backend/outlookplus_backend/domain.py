from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


# Cross-module conceptual types
UserId = str
EmailId = int
MailboxMessageId = str
UtcTimestamp = str


@dataclass(frozen=True)
class ParsedEmail:
    subject: Optional[str]
    from_addr: Optional[str]
    to_addrs: Optional[str]
    cc_addrs: Optional[str]
    sent_at_utc: Optional[UtcTimestamp]
    received_at_utc: UtcTimestamp
    body_text: Optional[str]
    body_html: Optional[str] = None


@dataclass(frozen=True)
class ParsedAttachment:
    filename: Optional[str]
    content_type: str
    size_bytes: Optional[int]


@dataclass(frozen=True)
class EmailMessage:
    id: EmailId
    user_id: UserId
    mailbox_message_id: MailboxMessageId

    folder: str
    is_read: bool
    labels: list[str]
    subject: Optional[str]
    from_addr: Optional[str]
    to_addrs: Optional[str]
    cc_addrs: Optional[str]
    sent_at_utc: Optional[UtcTimestamp]
    received_at_utc: UtcTimestamp

    preview_text: Optional[str]
    body_text: Optional[str]

    body_html: Optional[str]


@dataclass(frozen=True)
class AttachmentMeta:
    id: int
    user_id: UserId
    email_id: EmailId
    filename: Optional[str]
    content_type: str
    size_bytes: Optional[int]
    storage_path: str


@dataclass(frozen=True)
class MeetingStatus:
    meeting_related: bool
    confidence: float
    rationale: Optional[str]
    source: str


ReplyNeedLabel = Literal["NEEDS_REPLY", "NO_REPLY_NEEDED", "UNSURE"]


@dataclass(frozen=True)
class ReplyNeedResult:
    label: ReplyNeedLabel
    confidence: float
    reasons: list[str]
    source: str
