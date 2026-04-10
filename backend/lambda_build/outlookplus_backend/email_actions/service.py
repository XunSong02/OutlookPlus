from __future__ import annotations

from dataclasses import dataclass

from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.repos import EmailActionRepositorySqlite, EmailRepositorySqlite


@dataclass(frozen=True)
class EmailActionService:
    db: Db

    def execute(self, *, user_id: str, mailbox_message_id: str, action: str) -> None:
        with self.db.connect() as conn:
            email_repo = EmailRepositorySqlite(conn)
            email_id = email_repo.get_email_id_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
            if email_id is None:
                raise KeyError("Email not found")
            EmailActionRepositorySqlite(conn).add_action_log(
                user_id=user_id,
                email_id=email_id,
                action=action,
                status="ok",
            )
