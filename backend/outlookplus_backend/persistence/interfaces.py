from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from outlookplus_backend.domain import AttachmentMeta, EmailMessage, ParsedAttachment, ParsedEmail


class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork":
        ...

    def __exit__(self, exc_type, exc, tb) -> None:
        ...


@dataclass(frozen=True)
class AttachmentFileStoreProtocol:
    # Marker/shape type; concrete class is in file_store.py
    attachments_dir: str


class EmailRepository(Protocol):
    def upsert_email(self, *, user_id: str, mailbox_message_id: str, email: ParsedEmail) -> int:
        ...

    def list_emails(self, *, user_id: str, limit: int, cursor_received_at_utc: Optional[str]) -> list[EmailMessage]:
        ...

    def get_email(self, *, user_id: str, email_id: int) -> Optional[EmailMessage]:
        ...


class AttachmentRepository(Protocol):
    def add_attachment(self, *, user_id: str, email_id: int, meta: ParsedAttachment, storage_path: str) -> int:
        ...

    def list_attachments(self, *, user_id: str, email_id: int) -> list[AttachmentMeta]:
        ...


class IngestionStateRepository(Protocol):
    def get_state(self, *, user_id: str) -> Optional[tuple[int, int]]:
        ...

    def set_state(self, *, user_id: str, uidvalidity: int, last_seen_uid: int) -> None:
        ...
