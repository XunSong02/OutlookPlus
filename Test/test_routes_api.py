"""
Unit tests for backend/outlookplus_backend/api/routes.py

Follows the test specification at test-specs/routes-api-spec.md exactly.
Each test is generated one-at-a-time and verified before proceeding.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path bootstrap – make ``outlookplus_backend`` importable from repo root.
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS_DIR.parent / "backend"
sys.path.insert(0, str(_BACKEND_ROOT))

from outlookplus_backend.api.models import (  # noqa: E402
    AiComposeRequest,
    AiComposeResponse,
    AiRequestRequest,
    AiRequestResponse,
    EmailActionRequest,
    EmailActionResponse,
    EmailDto,
    EmailListResponse,
    EmailSenderDto,
    MeetingCheckResponse,
    PatchEmailRequest,
    ReplyNeedFeedbackRequest,
    ReplyNeedRequest,
    ReplyNeedResponse,
    SendEmailRequest,
    SendEmailResponse,
)
from outlookplus_backend.api.routes import (  # noqa: E402
    _sender_from_from_addr,
    _body_to_html,
    _parse_recipients,
    list_emails,
    get_email,
    get_email_route,
    patch_email,
    send_email,
    email_actions,
    ai_request,
    ai_compose,
    meeting_check,
    reply_need,
    reply_need_feedback,
)
from outlookplus_backend.domain import ParsedEmail, EmailMessage  # noqa: E402
from outlookplus_backend.persistence.db import Db  # noqa: E402
from outlookplus_backend.persistence.repos import EmailRepositorySqlite  # noqa: E402
from outlookplus_backend.utils.time import now_utc_rfc3339  # noqa: E402

from fastapi import HTTPException  # noqa: E402


# ======================================================================
# Helpers
# ======================================================================

@contextmanager
def _temp_environ(overrides: dict[str, str | None]):
    """Context manager that temporarily sets / clears env vars."""
    old = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _make_db(tmp_dir: str) -> Db:
    db_path = str(Path(tmp_dir) / "test-routes.db")
    db = Db(db_path=db_path)
    db.init_schema()
    return db


def _seed_email(
    *,
    db: Db,
    user_id: str,
    mailbox_message_id: str,
    subject: str = "Hello",
    body_text: str = "Line1\n\nLine2",
    body_html: str | None = None,
    folder: str = "inbox",
) -> None:
    now = now_utc_rfc3339()
    parsed = ParsedEmail(
        subject=subject,
        from_addr="Alice Smith <alice@example.com>",
        to_addrs="you@example.com",
        cc_addrs=None,
        sent_at_utc=now,
        received_at_utc=now,
        body_text=body_text,
    )
    with db.connect() as conn:
        EmailRepositorySqlite(conn).upsert_email(
            user_id=user_id,
            mailbox_message_id=mailbox_message_id,
            email=parsed,
            folder=folder,
            is_read=False,
            labels=["Important"],
            preview_text="Preview text",
            body_html=body_html,
        )


class _FakeSmtp:
    """Minimal stand-in for SmtpClient."""
    def __init__(self) -> None:
        self.sent: list[tuple[str, list[str], bytes]] = []

    def get_from_addr(self) -> str:
        return "demo@example.com"

    def send(self, *, user_id: str, from_addr: str, to_addrs: list[str], mime_message_bytes: bytes) -> None:
        self.sent.append((from_addr, list(to_addrs), bytes(mime_message_bytes)))


class _FakeAnalysisService:
    """Returns a canned AI analysis dict keyed by email id."""
    def __init__(self, analysis: dict[int, dict] | None = None) -> None:
        self._analysis = analysis or {}

    def get_for_emails(self, *, user_id: str, emails: list) -> dict:
        return self._analysis

    def get_for_email(self, *, user_id: str, email: Any) -> dict:
        return self._analysis.get(email.id, {
            "category": "Work",
            "sentiment": "neutral",
            "summary": "",
            "suggestedActions": [],
        })


# ======================================================================
# Test suite
# ======================================================================

class TestSenderFromFromAddr(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 1
    # ------------------------------------------------------------------
    def test_full_name_email_format(self):
        """sender parse: full 'Name <email>' format"""
        result = _sender_from_from_addr("Alice Smith <alice@example.com>")
        self.assertEqual(result.name, "Alice Smith")
        self.assertEqual(result.email, "alice@example.com")
        self.assertIsNone(result.avatar)

    # ------------------------------------------------------------------
    # Test 2
    # ------------------------------------------------------------------
    def test_none_falls_back_to_defaults(self):
        """sender parse: None falls back to defaults"""
        result = _sender_from_from_addr(None)
        self.assertEqual(result.name, "Unknown")
        self.assertEqual(result.email, "unknown@example.com")


class TestBodyToHtml(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 3
    # ------------------------------------------------------------------
    def test_converts_text_with_newlines_to_html(self):
        """body to html: converts text with newlines to HTML"""
        result = _body_to_html("Hello <world>\n\nPara2\nLine2")
        self.assertEqual(result, "<p>Hello &lt;world&gt;</p><p>Para2<br/>Line2</p>")

    # ------------------------------------------------------------------
    # Test 4
    # ------------------------------------------------------------------
    def test_none_returns_empty_string(self):
        """body to html: None returns empty string"""
        self.assertEqual(_body_to_html(None), "")


class TestParseRecipients(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 5
    # ------------------------------------------------------------------
    def test_multiple_addresses_with_dedup(self):
        """parse recipients: multiple addresses with dedup"""
        result = _parse_recipients("alice@a.com, Bob <bob@b.com>, Alice@A.com")
        self.assertEqual(result, ["alice@a.com", "bob@b.com"])


class TestListEmails(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 6
    # ------------------------------------------------------------------
    def test_returns_items_with_ai_analysis_and_cursor(self):
        """list_emails: returns items with AI analysis and pagination cursor"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-2", subject="Second")

            from outlookplus_backend.email_analysis import EmailAnalysisService
            analysis_svc = EmailAnalysisService(db=db)

            result = list_emails(
                folder="inbox",
                label=None,
                limit=2,
                cursor=None,
                user_id=user_id,
                db=db,
                analysis_service=analysis_svc,
            )
            self.assertIsInstance(result, EmailListResponse)
            self.assertEqual(len(result.items), 2)
            # Each item should be enriched with AI analysis
            for item in result.items:
                self.assertIn("category", item.aiAnalysis.model_dump())
            # nextCursor should be last email's date when len == limit
            self.assertIsNotNone(result.nextCursor)


class TestGetEmail(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 7
    # ------------------------------------------------------------------
    def test_returns_full_email_dto_with_body(self):
        """get_email: returns full EmailDto with body_html fallback"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            # Seed with body_html=None so fallback to _body_to_html is exercised
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1",
                        body_text="Hello", body_html=None)

            from outlookplus_backend.email_analysis import EmailAnalysisService
            analysis_svc = EmailAnalysisService(db=db)

            result = get_email(
                email_id="msg-1", user_id=user_id, db=db,
                analysis_service=analysis_svc,
            )
            self.assertIsInstance(result, EmailDto)
            self.assertEqual(result.body, "<p>Hello</p>")

    # ------------------------------------------------------------------
    # Test 8
    # ------------------------------------------------------------------
    def test_email_not_found_raises_404(self):
        """get_email: email not found raises 404"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            from outlookplus_backend.email_analysis import EmailAnalysisService
            analysis_svc = EmailAnalysisService(db=db)

            with self.assertRaises(HTTPException) as ctx:
                get_email(
                    email_id="nonexistent", user_id="demo", db=db,
                    analysis_service=analysis_svc,
                )
            self.assertEqual(ctx.exception.status_code, 404)


class TestGetEmailRoute(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 9
    # ------------------------------------------------------------------
    def test_delegates_to_get_email(self):
        """get_email_route: delegates to get_email and returns same EmailDto"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.email_analysis import EmailAnalysisService
            analysis_svc = EmailAnalysisService(db=db)

            result = get_email_route(
                email_id="msg-1", user_id=user_id, db=db,
                analysis_service=analysis_svc, analysis_classifier=None,
            )
            expected = get_email(
                email_id="msg-1", user_id=user_id, db=db,
                analysis_service=analysis_svc,
            )
            self.assertEqual(result.id, expected.id)
            self.assertEqual(result.subject, expected.subject)


class TestPatchEmail(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 10
    # ------------------------------------------------------------------
    def test_sets_read_status_returns_204(self):
        """patch_email: sets read status returns 204"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            resp = patch_email(
                email_id="msg-1",
                body=PatchEmailRequest(read=True),
                user_id=user_id,
                db=db,
            )
            self.assertEqual(resp.status_code, 204)

    # ------------------------------------------------------------------
    # Test 11
    # ------------------------------------------------------------------
    def test_read_none_raises_400(self):
        """patch_email: read is None raises 400"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            with self.assertRaises(HTTPException) as ctx:
                patch_email(
                    email_id="msg-1",
                    body=PatchEmailRequest(read=None),
                    user_id="demo",
                    db=db,
                )
            self.assertEqual(ctx.exception.status_code, 400)


class TestSendEmail(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 12
    # ------------------------------------------------------------------
    def test_success_sends_via_smtp_and_persists(self):
        """send_email: success sends via SMTP and persists to DB"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"

            from outlookplus_backend.credentials import CredentialStore
            store = CredentialStore(db=db)

            with _temp_environ({
                "OUTLOOKPLUS_SMTP_HOST": "example.com",
                "OUTLOOKPLUS_SMTP_USERNAME": "demo@example.com",
                "OUTLOOKPLUS_SMTP_PASSWORD": "pw",
            }):
                # Monkey-patch get_smtp_for_user so it uses our fake smtp
                import outlookplus_backend.api.routes as _routes_mod
                fake_smtp = _FakeSmtp()
                orig_fn = _routes_mod.get_smtp_for_user
                _routes_mod.get_smtp_for_user = lambda uid: fake_smtp
                try:
                    resp = send_email(
                        body=SendEmailRequest(to="a@b.com", subject="Hi", body="Hello"),
                        user_id=user_id,
                        db=db,
                        store=store,
                    )
                finally:
                    _routes_mod.get_smtp_for_user = orig_fn

            self.assertIsInstance(resp, SendEmailResponse)
            self.assertTrue(resp.id.startswith("sent_"))
            self.assertEqual(resp.to, "a@b.com")
            self.assertEqual(resp.subject, "Hi")
            # SMTP was called
            self.assertEqual(len(fake_smtp.sent), 1)
            # Email persisted in "sent" folder
            with db.connect() as conn:
                repo = EmailRepositorySqlite(conn)
                sent_items = repo.list_emails(
                    user_id=user_id, folder="sent", label=None,
                    limit=10, cursor_received_at_utc=None,
                )
            self.assertEqual(len(sent_items), 1)


class TestEmailActions(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 13
    # ------------------------------------------------------------------
    def test_success_returns_ok(self):
        """email_actions: success returns ok"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.email_actions import EmailActionService
            svc = EmailActionService(db=db)

            resp = email_actions(
                body=EmailActionRequest(emailId="msg-1", action="archive"),
                user_id=user_id,
                svc=svc,
            )
            self.assertIsInstance(resp, EmailActionResponse)
            self.assertEqual(resp.status, "ok")


class TestAiRequest(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 14
    # ------------------------------------------------------------------
    def test_returns_ai_response_text(self):
        """ai_request: returns AI response text"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.ai_assistant import AiAssistantService
            from outlookplus_backend.llm import PromptBuilder, GeminiClient, RateLimiter, RetryPolicy, StrictJsonValidator
            svc = AiAssistantService(
                db=db,
                prompt_builder=PromptBuilder(),
                gemini=GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy()),
                validator=StrictJsonValidator(),
            )

            resp = ai_request(
                body=AiRequestRequest(emailId="msg-1", prompt="Summarize"),
                user_id=user_id,
                svc=svc,
            )
            self.assertIsInstance(resp, AiRequestResponse)
            self.assertEqual(resp.emailId, "msg-1")
            self.assertTrue(resp.responseText)  # non-empty


class TestAiCompose(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 15
    # ------------------------------------------------------------------
    def test_returns_revised_text(self):
        """ai_compose: returns revised text"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            from outlookplus_backend.ai_assistant import AiAssistantService
            from outlookplus_backend.llm import PromptBuilder, GeminiClient, RateLimiter, RetryPolicy, StrictJsonValidator
            svc = AiAssistantService(
                db=db,
                prompt_builder=PromptBuilder(),
                gemini=GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy()),
                validator=StrictJsonValidator(),
            )

            resp = ai_compose(
                body=AiComposeRequest(body="Draft text"),
                user_id="demo",
                svc=svc,
            )
            self.assertIsInstance(resp, AiComposeResponse)
            self.assertTrue(resp.revisedText)
            self.assertIn(resp.source, {"gemini", "default"})


class TestMeetingCheck(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 16
    # ------------------------------------------------------------------
    def test_returns_meeting_classification(self):
        """meeting_check: returns meeting classification"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.meeting import MeetingService
            meeting_svc = MeetingService(db=db)

            resp = meeting_check(
                messageId="msg-1",
                user_id=user_id,
                db=db,
                meeting_service=meeting_svc,
            )
            self.assertIsInstance(resp, MeetingCheckResponse)
            self.assertEqual(resp.messageId, "msg-1")
            self.assertIsInstance(resp.meetingRelated, bool)
            self.assertIsInstance(resp.confidence, float)
            self.assertTrue(resp.source)


class TestReplyNeed(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 17
    # ------------------------------------------------------------------
    def test_returns_classification_result(self):
        """reply_need: returns classification result"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.meeting import MeetingService
            from outlookplus_backend.reply_need import ReplyNeedService
            from outlookplus_backend.config import ReplyNeedConfig
            from outlookplus_backend.llm import PromptBuilder, GeminiClient, RateLimiter, RetryPolicy, StrictJsonValidator

            meeting_svc = MeetingService(db=db)
            svc = ReplyNeedService(
                db=db,
                meeting_service=meeting_svc,
                prompt_builder=PromptBuilder(),
                gemini=GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy()),
                validator=StrictJsonValidator(),
                config=ReplyNeedConfig(min_confidence=0.65),
            )

            resp = reply_need(
                body=ReplyNeedRequest(messageId="msg-1"),
                user_id=user_id,
                svc=svc,
            )
            self.assertIsInstance(resp, ReplyNeedResponse)
            self.assertEqual(resp.messageId, "msg-1")
            self.assertTrue(resp.label)
            self.assertIsInstance(resp.confidence, float)
            self.assertIsInstance(resp.reasons, list)
            self.assertTrue(resp.source)


class TestReplyNeedFeedback(unittest.TestCase):
    # ------------------------------------------------------------------
    # Test 18
    # ------------------------------------------------------------------
    def test_valid_label_returns_204(self):
        """reply_need_feedback: valid label returns 204"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            _seed_email(db=db, user_id=user_id, mailbox_message_id="msg-1")

            from outlookplus_backend.meeting import MeetingService
            from outlookplus_backend.reply_need import ReplyNeedService
            from outlookplus_backend.config import ReplyNeedConfig
            from outlookplus_backend.llm import PromptBuilder, GeminiClient, RateLimiter, RetryPolicy, StrictJsonValidator

            svc = ReplyNeedService(
                db=db,
                meeting_service=MeetingService(db=db),
                prompt_builder=PromptBuilder(),
                gemini=GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy()),
                validator=StrictJsonValidator(),
                config=ReplyNeedConfig(min_confidence=0.65),
            )

            resp = reply_need_feedback(
                body=ReplyNeedFeedbackRequest(messageId="msg-1", userLabel="NEEDS_REPLY", comment="Agree"),
                user_id=user_id,
                svc=svc,
            )
            self.assertEqual(resp.status_code, 204)

    # ------------------------------------------------------------------
    # Test 19
    # ------------------------------------------------------------------
    def test_invalid_user_label_raises_400(self):
        """reply_need_feedback: invalid userLabel raises 400"""
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)

            from outlookplus_backend.meeting import MeetingService
            from outlookplus_backend.reply_need import ReplyNeedService
            from outlookplus_backend.config import ReplyNeedConfig
            from outlookplus_backend.llm import PromptBuilder, GeminiClient, RateLimiter, RetryPolicy, StrictJsonValidator

            svc = ReplyNeedService(
                db=db,
                meeting_service=MeetingService(db=db),
                prompt_builder=PromptBuilder(),
                gemini=GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy()),
                validator=StrictJsonValidator(),
                config=ReplyNeedConfig(min_confidence=0.65),
            )

            with self.assertRaises(HTTPException) as ctx:
                reply_need_feedback(
                    body=ReplyNeedFeedbackRequest(messageId="msg-1", userLabel="INVALID"),
                    user_id="demo",
                    svc=svc,
                )
            self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
