from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from outlookplus_backend.domain import (
    AttachmentMeta,
    EmailMessage,
    MeetingStatus,
    ParsedAttachment,
    ParsedEmail,
    ReplyNeedResult,
)
from outlookplus_backend.utils.time import now_utc_rfc3339


def _parse_labels(labels_json: object) -> list[str]:
    if labels_json is None:
        return []
    try:
        parsed = json.loads(str(labels_json))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for x in parsed:
        if isinstance(x, str) and x.strip():
            out.append(x)
    return out


@dataclass(frozen=True)
class EmailRepositorySqlite:
    conn: sqlite3.Connection

    def upsert_email(
        self,
        *,
        user_id: str,
        mailbox_message_id: str,
        email: ParsedEmail,
        folder: str = "inbox",
        is_read: bool = False,
        labels: list[str] | None = None,
        preview_text: str | None = None,
        body_html: str | None = None,
    ) -> int:
        created_at = now_utc_rfc3339()
        labels_json = json.dumps(labels or [], ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO emails(
                user_id, mailbox_message_id, folder, is_read, labels_json,
                subject, from_addr, to_addrs, cc_addrs,
                sent_at_utc, received_at_utc,
                preview_text, body_text, body_html,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, mailbox_message_id) DO UPDATE SET
                folder=excluded.folder,
                is_read=excluded.is_read,
                labels_json=excluded.labels_json,
                subject=excluded.subject,
                from_addr=excluded.from_addr,
                to_addrs=excluded.to_addrs,
                cc_addrs=excluded.cc_addrs,
                sent_at_utc=excluded.sent_at_utc,
                received_at_utc=excluded.received_at_utc,
                preview_text=excluded.preview_text,
                body_text=excluded.body_text,
                body_html=excluded.body_html
            """,
            (
                user_id,
                mailbox_message_id,
                folder,
                1 if is_read else 0,
                labels_json,
                email.subject,
                email.from_addr,
                email.to_addrs,
                email.cc_addrs,
                email.sent_at_utc,
                email.received_at_utc,
                preview_text,
                email.body_text,
                body_html,
                created_at,
            ),
        )
        row = self.conn.execute(
            "SELECT id FROM emails WHERE user_id=? AND mailbox_message_id=?",
            (user_id, mailbox_message_id),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def list_emails(
        self,
        *,
        user_id: str,
        folder: str | None = None,
        label: str | None = None,
        limit: int,
        cursor_received_at_utc: Optional[str],
    ) -> list[EmailMessage]:
        where = ["user_id=?"]
        params: list[object] = [user_id]

        if folder is not None:
            where.append("folder=?")
            params.append(folder)
        if label is not None:
            where.append("labels_json LIKE ?")
            params.append(f'%"{label}"%')
        if cursor_received_at_utc:
            where.append("received_at_utc < ?")
            params.append(cursor_received_at_utc)

        sql = (
            "SELECT * FROM emails WHERE "
            + " AND ".join(where)
            + " ORDER BY received_at_utc DESC LIMIT ?"
        )
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [
            EmailMessage(
                id=int(r["id"]),
                user_id=str(r["user_id"]),
                mailbox_message_id=str(r["mailbox_message_id"]),
                folder=str(r["folder"]),
                is_read=bool(r["is_read"]),
                labels=_parse_labels(r["labels_json"]),
                subject=r["subject"],
                from_addr=r["from_addr"],
                to_addrs=r["to_addrs"],
                cc_addrs=r["cc_addrs"],
                sent_at_utc=r["sent_at_utc"],
                received_at_utc=str(r["received_at_utc"]),
                preview_text=r["preview_text"],
                body_text=r["body_text"],
                body_html=r["body_html"],
            )
            for r in rows
        ]

    def get_email(self, *, user_id: str, email_id: int) -> Optional[EmailMessage]:
        r = self.conn.execute(
            "SELECT * FROM emails WHERE id=? AND user_id=?",
            (email_id, user_id),
        ).fetchone()
        if not r:
            return None
        return EmailMessage(
            id=int(r["id"]),
            user_id=str(r["user_id"]),
            mailbox_message_id=str(r["mailbox_message_id"]),
            folder=str(r["folder"]),
            is_read=bool(r["is_read"]),
            labels=_parse_labels(r["labels_json"]),
            subject=r["subject"],
            from_addr=r["from_addr"],
            to_addrs=r["to_addrs"],
            cc_addrs=r["cc_addrs"],
            sent_at_utc=r["sent_at_utc"],
            received_at_utc=str(r["received_at_utc"]),
            preview_text=r["preview_text"],
            body_text=r["body_text"],
            body_html=r["body_html"],
        )

    def get_email_id_by_message_id(self, *, user_id: str, mailbox_message_id: str) -> Optional[int]:
        r = self.conn.execute(
            "SELECT id FROM emails WHERE user_id=? AND mailbox_message_id=?",
            (user_id, mailbox_message_id),
        ).fetchone()
        if not r:
            return None
        return int(r["id"])

    def get_email_by_message_id(self, *, user_id: str, mailbox_message_id: str) -> Optional[EmailMessage]:
        r = self.conn.execute(
            "SELECT * FROM emails WHERE user_id=? AND mailbox_message_id=?",
            (user_id, mailbox_message_id),
        ).fetchone()
        if not r:
            return None
        return EmailMessage(
            id=int(r["id"]),
            user_id=str(r["user_id"]),
            mailbox_message_id=str(r["mailbox_message_id"]),
            folder=str(r["folder"]),
            is_read=bool(r["is_read"]),
            labels=_parse_labels(r["labels_json"]),
            subject=r["subject"],
            from_addr=r["from_addr"],
            to_addrs=r["to_addrs"],
            cc_addrs=r["cc_addrs"],
            sent_at_utc=r["sent_at_utc"],
            received_at_utc=str(r["received_at_utc"]),
            preview_text=r["preview_text"],
            body_text=r["body_text"],
            body_html=r["body_html"],
        )

    def set_read(self, *, user_id: str, mailbox_message_id: str, read: bool) -> bool:
        cur = self.conn.execute(
            "UPDATE emails SET is_read=? WHERE user_id=? AND mailbox_message_id=?",
            (1 if read else 0, user_id, mailbox_message_id),
        )
        return int(cur.rowcount or 0) > 0


@dataclass(frozen=True)
class AttachmentRepositorySqlite:
    conn: sqlite3.Connection

    def add_attachment(self, *, user_id: str, email_id: int, meta: ParsedAttachment, storage_path: str) -> int:
        created_at = now_utc_rfc3339()
        cur = self.conn.execute(
            """
            INSERT INTO attachments(user_id, email_id, filename, content_type, size_bytes, storage_path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                email_id,
                meta.filename,
                meta.content_type,
                meta.size_bytes,
                storage_path,
                created_at,
            ),
        )
        return int(cur.lastrowid)

    def list_attachments(self, *, user_id: str, email_id: int) -> list[AttachmentMeta]:
        rows = self.conn.execute(
            "SELECT * FROM attachments WHERE user_id=? AND email_id=? ORDER BY id ASC",
            (user_id, email_id),
        ).fetchall()
        return [
            AttachmentMeta(
                id=int(r["id"]),
                user_id=str(r["user_id"]),
                email_id=int(r["email_id"]),
                filename=r["filename"],
                content_type=str(r["content_type"]),
                size_bytes=r["size_bytes"],
                storage_path=str(r["storage_path"]),
            )
            for r in rows
        ]

    def get_first_attachment_path_by_type(self, *, user_id: str, email_id: int, content_type: str) -> Optional[str]:
        r = self.conn.execute(
            """
            SELECT storage_path FROM attachments
            WHERE user_id=? AND email_id=? AND content_type=?
            ORDER BY id ASC
            LIMIT 1
            """,
            (user_id, email_id, content_type),
        ).fetchone()
        if not r:
            return None
        return str(r["storage_path"])


@dataclass(frozen=True)
class MeetingRepositorySqlite:
    conn: sqlite3.Connection

    def get_status(self, *, user_id: str, email_id: int) -> Optional[MeetingStatus]:
        r = self.conn.execute(
            "SELECT * FROM meeting_classifications WHERE user_id=? AND email_id=?",
            (user_id, email_id),
        ).fetchone()
        if not r:
            return None
        return MeetingStatus(
            meeting_related=bool(r["meeting_related"]),
            confidence=float(r["confidence"]),
            rationale=r["rationale"],
            source=str(r["source"]),
        )

    def upsert(self, *, user_id: str, email_id: int, meeting_related: bool, confidence: float, rationale: str | None, source: str) -> None:
        created_at = now_utc_rfc3339()
        self.conn.execute(
            """
            INSERT INTO meeting_classifications(user_id, email_id, meeting_related, confidence, rationale, source, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, email_id) DO UPDATE SET
                meeting_related=excluded.meeting_related,
                confidence=excluded.confidence,
                rationale=excluded.rationale,
                source=excluded.source
            """,
            (user_id, email_id, 1 if meeting_related else 0, confidence, rationale, source, created_at),
        )


@dataclass(frozen=True)
class ReplyNeedRepositorySqlite:
    conn: sqlite3.Connection

    def get(self, *, user_id: str, email_id: int) -> Optional[tuple[int, ReplyNeedResult]]:
        r = self.conn.execute(
            "SELECT * FROM reply_need_classifications WHERE user_id=? AND email_id=?",
            (user_id, email_id),
        ).fetchone()
        if not r:
            return None
        reasons = json.loads(str(r["reasons_json"]))
        result = ReplyNeedResult(
            label=str(r["label"]),
            confidence=float(r["confidence"]),
            reasons=list(reasons),
            source=str(r["source"]),
        )
        return int(r["id"]), result

    def upsert(self, *, user_id: str, email_id: int, result: ReplyNeedResult) -> int:
        created_at = now_utc_rfc3339()
        reasons_json = json.dumps(result.reasons, ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO reply_need_classifications(user_id, email_id, label, confidence, reasons_json, source, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, email_id) DO UPDATE SET
                label=excluded.label,
                confidence=excluded.confidence,
                reasons_json=excluded.reasons_json,
                source=excluded.source
            """,
            (user_id, email_id, result.label, result.confidence, reasons_json, result.source, created_at),
        )
        r = self.conn.execute(
            "SELECT id FROM reply_need_classifications WHERE user_id=? AND email_id=?",
            (user_id, email_id),
        ).fetchone()
        assert r is not None
        return int(r["id"])

    def add_feedback(self, *, user_id: str, email_id: int, classification_id: int | None, user_label: str, comment: str | None) -> None:
        created_at = now_utc_rfc3339()
        self.conn.execute(
            """
            INSERT INTO reply_need_feedback(user_id, email_id, classification_id, user_label, comment, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email_id, classification_id, user_label, comment, created_at),
        )


@dataclass(frozen=True)
class IngestionStateRepositorySqlite:
    conn: sqlite3.Connection

    def get_state(self, *, user_id: str) -> Optional[tuple[int, int]]:
        r = self.conn.execute(
            "SELECT imap_uidvalidity, last_seen_uid FROM ingestion_state WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not r:
            return None
        return int(r["imap_uidvalidity"]), int(r["last_seen_uid"])

    def set_state(self, *, user_id: str, uidvalidity: int, last_seen_uid: int) -> None:
        updated_at = now_utc_rfc3339()
        self.conn.execute(
            """
            INSERT INTO ingestion_state(user_id, imap_uidvalidity, last_seen_uid, updated_at_utc)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                imap_uidvalidity=excluded.imap_uidvalidity,
                last_seen_uid=excluded.last_seen_uid,
                updated_at_utc=excluded.updated_at_utc
            """,
            (user_id, uidvalidity, last_seen_uid, updated_at),
        )


@dataclass(frozen=True)
class EmailAnalysisRepositorySqlite:
    conn: sqlite3.Connection

    def get_by_email_id(self, *, user_id: str, email_id: int) -> Optional[dict[str, object]]:
        r = self.conn.execute(
            "SELECT * FROM email_ai_analysis WHERE user_id=? AND email_id=?",
            (user_id, email_id),
        ).fetchone()
        if not r:
            return None
        try:
            actions = json.loads(str(r["suggested_actions_json"]))
        except Exception:
            actions = []
        if not isinstance(actions, list):
            actions = []
        return {
            "category": str(r["category"]),
            "sentiment": str(r["sentiment"]),
            "summary": str(r["summary"]),
            "suggestedActions": list(actions),
            "source": str(r["source"]),
        }

    def get_by_email_ids(self, *, user_id: str, email_ids: list[int]) -> dict[int, dict[str, object]]:
        if not email_ids:
            return {}
        placeholders = ",".join(["?"] * len(email_ids))
        rows = self.conn.execute(
            f"SELECT * FROM email_ai_analysis WHERE user_id=? AND email_id IN ({placeholders})",
            [user_id, *email_ids],
        ).fetchall()
        out: dict[int, dict[str, object]] = {}
        for r in rows:
            try:
                actions = json.loads(str(r["suggested_actions_json"]))
            except Exception:
                actions = []
            if not isinstance(actions, list):
                actions = []
            out[int(r["email_id"])] = {
                "category": str(r["category"]),
                "sentiment": str(r["sentiment"]),
                "summary": str(r["summary"]),
                "suggestedActions": list(actions),
                "source": str(r["source"]),
            }
        return out

    def upsert_analysis(
        self,
        *,
        user_id: str,
        email_id: int,
        category: str,
        sentiment: str,
        summary: str,
        suggested_actions: list[object],
        source: str,
    ) -> None:
        created_at = now_utc_rfc3339()
        actions_json = json.dumps(list(suggested_actions), ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO email_ai_analysis(
                user_id, email_id, category, sentiment, summary,
                suggested_actions_json, source, created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, email_id) DO UPDATE SET
                category=excluded.category,
                sentiment=excluded.sentiment,
                summary=excluded.summary,
                suggested_actions_json=excluded.suggested_actions_json,
                source=excluded.source
            """,
            (user_id, email_id, category, sentiment, summary, actions_json, source, created_at),
        )


@dataclass(frozen=True)
class AiRequestRepositorySqlite:
    conn: sqlite3.Connection

    def add_request(
        self,
        *,
        user_id: str,
        email_id: int,
        prompt_text: str,
        response_text: str,
        source: str,
    ) -> int:
        created_at = now_utc_rfc3339()
        cur = self.conn.execute(
            """
            INSERT INTO ai_requests(user_id, email_id, prompt_text, response_text, source, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email_id, prompt_text, response_text, source, created_at),
        )
        return int(cur.lastrowid)


@dataclass(frozen=True)
class EmailActionRepositorySqlite:
    conn: sqlite3.Connection

    def add_action_log(self, *, user_id: str, email_id: int, action: str, status: str) -> int:
        created_at = now_utc_rfc3339()
        cur = self.conn.execute(
            """
            INSERT INTO email_action_logs(user_id, email_id, action, status, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email_id, action, status, created_at),
        )
        return int(cur.lastrowid)
