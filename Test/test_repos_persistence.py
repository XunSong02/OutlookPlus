"""
Unit tests for backend/outlookplus_backend/persistence/repos.py

Follows the test specification at test-specs/repos-persistence-spec.md exactly.
Uses an in-memory SQLite database (via a temporary directory) with the real
schema so that every repository class runs against identical table structures
to production.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the backend package importable when running from the repo root.
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS_DIR.parent / "backend"
sys.path.insert(0, str(_BACKEND_ROOT))

from outlookplus_backend.domain import (  # noqa: E402
    AttachmentMeta,
    EmailMessage,
    MeetingStatus,
    ParsedAttachment,
    ParsedEmail,
    ReplyNeedResult,
)
from outlookplus_backend.persistence.db import Db  # noqa: E402
from outlookplus_backend.persistence.repos import (  # noqa: E402
    AiRequestRepositorySqlite,
    AttachmentRepositorySqlite,
    EmailActionRepositorySqlite,
    EmailAnalysisRepositorySqlite,
    EmailRepositorySqlite,
    IngestionStateRepositorySqlite,
    MeetingRepositorySqlite,
    ReplyNeedRepositorySqlite,
    _parse_labels,
)
from outlookplus_backend.utils.time import now_utc_rfc3339  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_dir: str) -> Db:
    """Create a fresh DB with the full schema in a temp directory."""
    db_path = str(Path(tmp_dir) / "test.db")
    db = Db(db_path=db_path)
    db.init_schema()
    return db


def _seed_email(
    conn,
    *,
    user_id: str = "user1",
    mailbox_message_id: str = "msg-1",
    folder: str = "inbox",
    is_read: bool = False,
    labels: list[str] | None = None,
    received_at_utc: str | None = None,
    subject: str = "Test Subject",
) -> int:
    """Insert a single email and return its id."""
    repo = EmailRepositorySqlite(conn)
    email = ParsedEmail(
        subject=subject,
        from_addr="Sender <sender@example.com>",
        to_addrs="recipient@example.com",
        cc_addrs=None,
        sent_at_utc=received_at_utc or now_utc_rfc3339(),
        received_at_utc=received_at_utc or now_utc_rfc3339(),
        body_text="Hello body text",
    )
    return repo.upsert_email(
        user_id=user_id,
        mailbox_message_id=mailbox_message_id,
        email=email,
        folder=folder,
        is_read=is_read,
        labels=labels or [],
        preview_text="Preview text",
        body_html="<p>Hello</p>",
    )


# ---------------------------------------------------------------------------
# Test 1 – _parse_labels: valid JSON array of strings
# ---------------------------------------------------------------------------

class TestParseLabels(unittest.TestCase):
    def test_parse_labels_valid_json_array(self):
        result = _parse_labels('["Work", "Urgent"]')
        self.assertEqual(result, ["Work", "Urgent"])

    # Test 2 – _parse_labels: None returns empty list
    def test_parse_labels_none_returns_empty_list(self):
        result = _parse_labels(None)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Test 3 – upsert_email: insert and retrieve new email
# ---------------------------------------------------------------------------

class TestEmailRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_upsert_email_insert_and_retrieve(self):
        with self.db.connect() as conn:
            email_id = _seed_email(
                conn,
                user_id="user1",
                mailbox_message_id="msg-1",
                folder="inbox",
                labels=["Work"],
            )
            self.assertGreater(email_id, 0)

            repo = EmailRepositorySqlite(conn)
            email = repo.get_email_by_message_id(
                user_id="user1", mailbox_message_id="msg-1"
            )
            self.assertIsNotNone(email)
            self.assertEqual(email.folder, "inbox")
            self.assertEqual(email.labels, ["Work"])

    # Test 4 – list_emails: filters by folder and respects limit and order
    def test_list_emails_folder_filter_limit_order(self):
        with self.db.connect() as conn:
            _seed_email(conn, mailbox_message_id="msg-a", folder="inbox",
                        received_at_utc="2025-01-01T00:00:00Z")
            _seed_email(conn, mailbox_message_id="msg-b", folder="inbox",
                        received_at_utc="2025-01-02T00:00:00Z")
            _seed_email(conn, mailbox_message_id="msg-c", folder="sent",
                        received_at_utc="2025-01-03T00:00:00Z")

            repo = EmailRepositorySqlite(conn)
            results = repo.list_emails(
                user_id="user1", folder="inbox", limit=10,
                cursor_received_at_utc=None,
            )

            self.assertEqual(len(results), 2)
            for e in results:
                self.assertEqual(e.folder, "inbox")
            # DESC order: newest first
            self.assertGreaterEqual(
                results[0].received_at_utc, results[1].received_at_utc
            )

    # Test 5 – get_email: found returns EmailMessage
    def test_get_email_found(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = EmailRepositorySqlite(conn)
            email = repo.get_email(user_id="user1", email_id=email_id)
            self.assertIsNotNone(email)
            self.assertIsInstance(email, EmailMessage)
            self.assertEqual(email.id, email_id)

    # Test 6 – get_email_id_by_message_id: found returns id
    def test_get_email_id_by_message_id_found(self):
        with self.db.connect() as conn:
            expected_id = _seed_email(conn, mailbox_message_id="msg-1")
            repo = EmailRepositorySqlite(conn)
            result_id = repo.get_email_id_by_message_id(
                user_id="user1", mailbox_message_id="msg-1"
            )
            self.assertEqual(result_id, expected_id)

    # Test 7 – get_email_by_message_id: found returns full EmailMessage
    def test_get_email_by_message_id_found(self):
        with self.db.connect() as conn:
            _seed_email(conn, mailbox_message_id="msg-1", subject="Test Subject")
            repo = EmailRepositorySqlite(conn)
            email = repo.get_email_by_message_id(
                user_id="user1", mailbox_message_id="msg-1"
            )
            self.assertIsNotNone(email)
            self.assertIsInstance(email, EmailMessage)
            self.assertEqual(email.subject, "Test Subject")
            self.assertEqual(email.mailbox_message_id, "msg-1")

    # Test 8 – set_read: marks email as read and returns True
    def test_set_read_marks_email_as_read(self):
        with self.db.connect() as conn:
            _seed_email(conn, mailbox_message_id="msg-1", is_read=False)
            repo = EmailRepositorySqlite(conn)
            result = repo.set_read(
                user_id="user1", mailbox_message_id="msg-1", read=True
            )
            self.assertTrue(result)
            email = repo.get_email_by_message_id(
                user_id="user1", mailbox_message_id="msg-1"
            )
            self.assertTrue(email.is_read)

    # Test 9 – set_read: nonexistent email returns False
    def test_set_read_nonexistent_returns_false(self):
        with self.db.connect() as conn:
            repo = EmailRepositorySqlite(conn)
            result = repo.set_read(
                user_id="user1", mailbox_message_id="nonexistent", read=True
            )
            self.assertFalse(result)


# ---------------------------------------------------------------------------
# Tests 10-12 – AttachmentRepository
# ---------------------------------------------------------------------------

class TestAttachmentRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 10 – add_attachment: inserts and returns id
    def test_add_attachment_inserts_and_returns_id(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = AttachmentRepositorySqlite(conn)
            att_id = repo.add_attachment(
                user_id="user1",
                email_id=email_id,
                meta=ParsedAttachment(
                    filename="doc.pdf",
                    content_type="application/pdf",
                    size_bytes=1024,
                ),
                storage_path="/files/doc.pdf",
            )
            self.assertGreater(att_id, 0)

    # Test 11 – list_attachments: returns all for email ordered by id
    def test_list_attachments_returns_ordered(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = AttachmentRepositorySqlite(conn)
            repo.add_attachment(
                user_id="user1", email_id=email_id,
                meta=ParsedAttachment(filename="a.txt", content_type="text/plain", size_bytes=10),
                storage_path="/files/a.txt",
            )
            repo.add_attachment(
                user_id="user1", email_id=email_id,
                meta=ParsedAttachment(filename="b.txt", content_type="text/plain", size_bytes=20),
                storage_path="/files/b.txt",
            )
            results = repo.list_attachments(user_id="user1", email_id=email_id)
            self.assertEqual(len(results), 2)
            self.assertIsInstance(results[0], AttachmentMeta)
            # ASC order
            self.assertLess(results[0].id, results[1].id)

    # Test 12 – get_first_attachment_path_by_type: found returns path
    def test_get_first_attachment_path_by_type_found(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = AttachmentRepositorySqlite(conn)
            repo.add_attachment(
                user_id="user1", email_id=email_id,
                meta=ParsedAttachment(filename="cal.ics", content_type="text/calendar", size_bytes=512),
                storage_path="/files/cal.ics",
            )
            path = repo.get_first_attachment_path_by_type(
                user_id="user1", email_id=email_id, content_type="text/calendar"
            )
            self.assertEqual(path, "/files/cal.ics")


# ---------------------------------------------------------------------------
# Tests 13-14 – MeetingRepository
# ---------------------------------------------------------------------------

class TestMeetingRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 13 – meeting get_status: upsert then retrieve
    def test_meeting_get_status_upsert_then_retrieve(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = MeetingRepositorySqlite(conn)
            repo.upsert(
                user_id="user1", email_id=email_id,
                meeting_related=True, confidence=0.95,
                rationale="Has date", source="gemini",
            )
            status = repo.get_status(user_id="user1", email_id=email_id)
            self.assertIsNotNone(status)
            self.assertIsInstance(status, MeetingStatus)
            self.assertTrue(status.meeting_related)
            self.assertAlmostEqual(status.confidence, 0.95)

    # Test 14 – meeting upsert: insert new classification
    def test_meeting_upsert_insert_new(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = MeetingRepositorySqlite(conn)
            repo.upsert(
                user_id="user1", email_id=email_id,
                meeting_related=True, confidence=0.9,
                rationale=None, source="gemini",
            )
            status = repo.get_status(user_id="user1", email_id=email_id)
            self.assertIsNotNone(status)
            self.assertTrue(status.meeting_related)


# ---------------------------------------------------------------------------
# Tests 15-17 – ReplyNeedRepository
# ---------------------------------------------------------------------------

class TestReplyNeedRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 15 – reply_need get: upsert then retrieve
    def test_reply_need_get_upsert_then_retrieve(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = ReplyNeedRepositorySqlite(conn)
            result_obj = ReplyNeedResult(
                label="NEEDS_REPLY", confidence=0.85,
                reasons=["Direct question"], source="gemini",
            )
            repo.upsert(user_id="user1", email_id=email_id, result=result_obj)
            got = repo.get(user_id="user1", email_id=email_id)
            self.assertIsNotNone(got)
            cls_id, result = got
            self.assertGreater(cls_id, 0)
            self.assertIsInstance(result, ReplyNeedResult)
            self.assertEqual(result.label, "NEEDS_REPLY")

    # Test 16 – reply_need upsert: insert and return id
    def test_reply_need_upsert_returns_id(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = ReplyNeedRepositorySqlite(conn)
            cls_id = repo.upsert(
                user_id="user1", email_id=email_id,
                result=ReplyNeedResult(
                    label="NEEDS_REPLY", confidence=0.85,
                    reasons=["Direct question"], source="gemini",
                ),
            )
            self.assertGreater(cls_id, 0)

    # Test 17 – reply_need add_feedback: inserts feedback record
    def test_reply_need_add_feedback(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            rn_repo = ReplyNeedRepositorySqlite(conn)
            cls_id = rn_repo.upsert(
                user_id="user1", email_id=email_id,
                result=ReplyNeedResult(
                    label="NEEDS_REPLY", confidence=0.85,
                    reasons=["Question"], source="gemini",
                ),
            )
            # Should not raise
            rn_repo.add_feedback(
                user_id="user1", email_id=email_id,
                classification_id=cls_id,
                user_label="NEEDS_REPLY", comment="Agree",
            )


# ---------------------------------------------------------------------------
# Tests 18-19 – IngestionStateRepository
# ---------------------------------------------------------------------------

class TestIngestionStateRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 18 – ingestion get_state: set then retrieve
    def test_ingestion_get_state_set_then_retrieve(self):
        with self.db.connect() as conn:
            repo = IngestionStateRepositorySqlite(conn)
            repo.set_state(user_id="user1", uidvalidity=100, last_seen_uid=500)
            result = repo.get_state(user_id="user1")
            self.assertIsNotNone(result)
            self.assertEqual(result, (100, 500))

    # Test 19 – ingestion set_state: insert new state
    def test_ingestion_set_state_insert_new(self):
        with self.db.connect() as conn:
            repo = IngestionStateRepositorySqlite(conn)
            repo.set_state(user_id="user1", uidvalidity=100, last_seen_uid=500)
            result = repo.get_state(user_id="user1")
            self.assertEqual(result, (100, 500))


# ---------------------------------------------------------------------------
# Tests 20-22 – EmailAnalysisRepository
# ---------------------------------------------------------------------------

class TestEmailAnalysisRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 20 – analysis get_by_email_id: upsert then retrieve
    def test_analysis_get_by_email_id_upsert_then_retrieve(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = EmailAnalysisRepositorySqlite(conn)
            repo.upsert_analysis(
                user_id="user1", email_id=email_id,
                category="Work", sentiment="positive", summary="Good",
                suggested_actions=[{"kind": "suggestion", "text": "Archive"}],
                source="gemini",
            )
            result = repo.get_by_email_id(user_id="user1", email_id=email_id)
            self.assertIsNotNone(result)
            self.assertEqual(result["category"], "Work")
            self.assertEqual(result["sentiment"], "positive")
            self.assertEqual(result["summary"], "Good")
            self.assertIsInstance(result["suggestedActions"], list)
            self.assertEqual(len(result["suggestedActions"]), 1)

    # Test 21 – analysis get_by_email_ids: batch retrieval + empty list
    def test_analysis_get_by_email_ids_batch(self):
        with self.db.connect() as conn:
            eid1 = _seed_email(conn, mailbox_message_id="msg-1")
            eid2 = _seed_email(conn, mailbox_message_id="msg-2")
            repo = EmailAnalysisRepositorySqlite(conn)
            for eid in (eid1, eid2):
                repo.upsert_analysis(
                    user_id="user1", email_id=eid,
                    category="Work", sentiment="positive", summary="Good",
                    suggested_actions=[], source="gemini",
                )
            result = repo.get_by_email_ids(
                user_id="user1", email_ids=[eid1, eid2]
            )
            self.assertIn(eid1, result)
            self.assertIn(eid2, result)

            # Empty list short-circuit
            empty = repo.get_by_email_ids(user_id="user1", email_ids=[])
            self.assertEqual(empty, {})

    # Test 22 – analysis upsert: insert new analysis
    def test_analysis_upsert_insert_new(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = EmailAnalysisRepositorySqlite(conn)
            repo.upsert_analysis(
                user_id="user1", email_id=email_id,
                category="Work", sentiment="positive", summary="Good",
                suggested_actions=[], source="gemini",
            )
            result = repo.get_by_email_id(user_id="user1", email_id=email_id)
            self.assertIsNotNone(result)
            self.assertEqual(result["category"], "Work")


# ---------------------------------------------------------------------------
# Test 23 – AiRequestRepository
# ---------------------------------------------------------------------------

class TestAiRequestRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 23 – ai_request add_request: inserts and returns id
    def test_ai_request_add_returns_id(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = AiRequestRepositorySqlite(conn)
            req_id = repo.add_request(
                user_id="user1", email_id=email_id,
                prompt_text="Summarize", response_text="Summary",
                source="gemini",
            )
            self.assertGreater(req_id, 0)


# ---------------------------------------------------------------------------
# Test 24 – EmailActionRepository
# ---------------------------------------------------------------------------

class TestEmailActionRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # Test 24 – action_log add_action_log: inserts and returns id
    def test_action_log_add_returns_id(self):
        with self.db.connect() as conn:
            email_id = _seed_email(conn)
            repo = EmailActionRepositorySqlite(conn)
            log_id = repo.add_action_log(
                user_id="user1", email_id=email_id,
                action="archive", status="ok",
            )
            self.assertGreater(log_id, 0)


if __name__ == "__main__":
    unittest.main()
