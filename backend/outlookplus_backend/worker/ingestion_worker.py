from __future__ import annotations

import time
from dataclasses import dataclass

from outlookplus_backend.config import load_storage_config
from outlookplus_backend.imap.client import MailboxClient, MailboxCursor
from outlookplus_backend.imap.normalizer import normalize_rfc822
from outlookplus_backend.email_analysis.classifier import EmailAnalysisClassifier
from outlookplus_backend.meeting.classifier import MeetingClassifier
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.persistence.file_store import AttachmentFileStore
from outlookplus_backend.persistence.repos import AttachmentRepositorySqlite, EmailRepositorySqlite, IngestionStateRepositorySqlite
from outlookplus_backend.persistence.unit_of_work import SqliteUnitOfWork


@dataclass(frozen=True)
class IngestionWorker:
    db: Db
    mailbox: MailboxClient
    meeting_classifier: MeetingClassifier
    email_analysis_classifier: EmailAnalysisClassifier

    def run_forever(self) -> None:
        while True:
            # In MVP, user_id must be provided by the caller of run_once.
            time.sleep(10)

    def run_once(self, *, user_id: str) -> int:
        # Read state
        with self.db.connect() as conn:
            state_repo = IngestionStateRepositorySqlite(conn)
            state = state_repo.get_state(user_id=user_id)

        cursor = MailboxCursor(uidvalidity=state[0], last_seen_uid=state[1]) if state else None
        messages = self.mailbox.list_new_messages(user_id=user_id, cursor=cursor)
        if not messages:
            return 0

        storage_cfg = load_storage_config()
        store = AttachmentFileStore(attachments_dir=storage_cfg.attachments_dir)

        ingested = 0
        max_uid = cursor.last_seen_uid if cursor else 0
        uidvalidity = messages[0].uidvalidity

        for m in messages:
            max_uid = max(max_uid, m.uid)
            normalized = normalize_rfc822(m.rfc822_bytes)
            mailbox_message_id = f"{m.uidvalidity}:{m.uid}"

            with SqliteUnitOfWork(self.db) as uow:
                conn = uow.cursor()
                email_repo = EmailRepositorySqlite(conn)
                preview = ((normalized.email.body_text or "").strip()[:160]) or (normalized.email.subject or "") or ""
                email_id = email_repo.upsert_email(
                    user_id=user_id,
                    mailbox_message_id=mailbox_message_id,
                    email=normalized.email,
                    folder="inbox",
                    is_read=False,
                    labels=[],
                    preview_text=preview,
                    body_html=normalized.email.body_html,
                )

                # Skip attachments if we already have any for this email (idempotency for at-least-once ingestion).
                existing = conn.execute(
                    "SELECT COUNT(1) AS n FROM attachments WHERE user_id=? AND email_id=?",
                    (user_id, email_id),
                ).fetchone()
                has_any = bool(existing and int(existing["n"]) > 0)

                if not has_any:
                    att_repo = AttachmentRepositorySqlite(conn)
                    for idx, (meta, data) in enumerate(normalized.attachments, start=1):
                        path = store.write_bytes(
                            user_id=user_id,
                            email_id=email_id,
                            attachment_id=idx,
                            content_type=meta.content_type,
                            data=data,
                        )
                        att_repo.add_attachment(user_id=user_id, email_id=email_id, meta=meta, storage_path=path)

            ingested += 1
            self.meeting_classifier.classify_if_needed(user_id=user_id, email_id=email_id)
            self.email_analysis_classifier.classify_if_needed(user_id=user_id, email_id=email_id)

        with self.db.connect() as conn:
            IngestionStateRepositorySqlite(conn).set_state(user_id=user_id, uidvalidity=uidvalidity, last_seen_uid=max_uid)

        return ingested
