from __future__ import annotations

from dataclasses import dataclass

from outlookplus_backend.domain import MeetingStatus
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailRepositorySqlite, MeetingRepositorySqlite


_DEFAULT = MeetingStatus(meeting_related=False, confidence=0.0, rationale=None, source="default")


@dataclass(frozen=True)
class MeetingService:
    db: Db

    def get_status(self, *, user_id: str, email_id: int) -> MeetingStatus:
        with self.db.connect() as conn:
            repo = MeetingRepositorySqlite(conn)
            status = repo.get_status(user_id=user_id, email_id=email_id)
            return status or _DEFAULT

    def get_status_by_message_id(self, *, user_id: str, mailbox_message_id: str) -> MeetingStatus:
        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email_id is None:
                return _DEFAULT
            meet_repo = MeetingRepositorySqlite(conn)
            status = meet_repo.get_status(user_id=user_id, email_id=email_id)
            return status or _DEFAULT
