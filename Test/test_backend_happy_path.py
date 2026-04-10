from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any


# Ensure `outlookplus_backend` is importable when running from repo root.
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS_DIR.parent / "backend"
sys.path.insert(0, str(_BACKEND_ROOT))


from outlookplus_backend.api.models import (  # noqa: E402
    AiComposeRequest,
    AiRequestRequest,
    EmailActionRequest,
    PatchEmailRequest,
    ReplyNeedFeedbackRequest,
    ReplyNeedRequest,
    SendEmailRequest,
)
from outlookplus_backend.api.routes import (  # noqa: E402
    ai_compose,
    ai_request,
    email_actions,
    get_email,
    list_emails,
    meeting_check,
    patch_email,
    reply_need,
    reply_need_feedback,
    send_email,
)
from outlookplus_backend.api.app import create_app  # noqa: E402
from outlookplus_backend.config import ReplyNeedConfig  # noqa: E402
from outlookplus_backend.domain import ParsedEmail  # noqa: E402
from outlookplus_backend.ai_assistant import AiAssistantService  # noqa: E402
from outlookplus_backend.email_actions import EmailActionService  # noqa: E402
from outlookplus_backend.email_analysis import EmailAnalysisClassifier, EmailAnalysisService  # noqa: E402
from outlookplus_backend.ics import IcsExtractor  # noqa: E402
from outlookplus_backend.llm import GeminiClient, PromptBuilder, RateLimiter, RetryPolicy, StrictJsonValidator  # noqa: E402
from outlookplus_backend.meeting import MeetingClassifier, MeetingService  # noqa: E402
from outlookplus_backend.persistence.db import Db  # noqa: E402
from outlookplus_backend.persistence.repos import EmailRepositorySqlite  # noqa: E402
from outlookplus_backend.reply_need import ReplyNeedService  # noqa: E402
from outlookplus_backend.utils.time import now_utc_rfc3339  # noqa: E402
from outlookplus_backend.worker.ingestion_worker import IngestionWorker  # noqa: E402


def _reset_wiring_caches() -> None:
    # Wiring uses lru_cache; tests swap env vars for DB paths.
    import outlookplus_backend.wiring as wiring

    for fn_name in [
        "get_db",
        "get_smtp_client",
        "get_meeting_service",
        "get_reply_need_service",
        "get_email_analysis_service",
        "get_ai_assistant_service",
        "get_email_action_service",
        "get_meeting_classifier",
        "get_email_analysis_classifier",
        "_prompt_builder",
        "_validator",
        "_gemini",
        "_ics",
    ]:
        fn = getattr(wiring, fn_name, None)
        if fn is not None and hasattr(fn, "cache_clear"):
            fn.cache_clear()  # type: ignore[attr-defined]


@contextmanager
def _temp_environ(overrides: dict[str, str | None]):
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
    db_path = str(Path(tmp_dir) / "outlookplus-test.db")
    db = Db(db_path=db_path)
    db.init_schema()
    return db


def _seed_one_email(*, db: Db, user_id: str, mailbox_message_id: str, subject: str = "Hello") -> None:
    now = now_utc_rfc3339()
    parsed = ParsedEmail(
        subject=subject,
        from_addr="Sender <sender@example.com>",
        to_addrs="you@example.com",
        cc_addrs=None,
        sent_at_utc=now,
        received_at_utc=now,
        body_text="Line1\n\nLine2",
    )
    with db.connect() as conn:
        EmailRepositorySqlite(conn).upsert_email(
            user_id=user_id,
            mailbox_message_id=mailbox_message_id,
            email=parsed,
            folder="inbox",
            is_read=False,
            labels=["Important"],
            preview_text="Preview text",
            body_html=None,
        )


class _FakeSmtp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, list[str], bytes]] = []

    def get_from_addr(self) -> str:
        return "demo@example.com"

    def send(self, *, user_id: str, from_addr: str, to_addrs: list[str], mime_message_bytes: bytes) -> None:
        self.sent.append((from_addr, list(to_addrs), bytes(mime_message_bytes)))


@dataclass(frozen=True)
class _FakeRawMailboxMessage:
    uidvalidity: int
    uid: int
    rfc822_bytes: bytes


class _FakeMailbox:
    def __init__(self, messages: list[_FakeRawMailboxMessage]):
        self._messages = messages

    def list_new_messages(self, *, user_id: str, cursor):
        return list(self._messages)


class BackendHappyPathTests(unittest.TestCase):
    def test_email_feed_detail_and_patch_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            mid = "999:1"
            _seed_one_email(db=db, user_id=user_id, mailbox_message_id=mid)

            analysis_service = EmailAnalysisService(db=db)

            feed = list_emails(
                folder="inbox",
                label=None,
                limit=50,
                cursor=None,
                user_id=user_id,
                db=db,
                analysis_service=analysis_service,
            )
            self.assertEqual(len(feed.items), 1)
            self.assertEqual(feed.items[0].id, mid)
            self.assertIn("category", feed.items[0].aiAnalysis.model_dump())

            detail = get_email(email_id=mid, user_id=user_id, db=db, analysis_service=analysis_service)
            self.assertEqual(detail.id, mid)
            self.assertTrue(detail.body.startswith("<p>"))
            self.assertFalse(detail.read)

            resp = patch_email(email_id=mid, body=PatchEmailRequest(read=True), user_id=user_id, db=db)
            self.assertEqual(resp.status_code, 204)

            detail2 = get_email(email_id=mid, user_id=user_id, db=db, analysis_service=analysis_service)
            self.assertTrue(detail2.read)

    def test_ai_actions_reply_need_and_meeting_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            mid = "999:2"
            _seed_one_email(db=db, user_id=user_id, mailbox_message_id=mid, subject="Need help")

            prompt_builder = PromptBuilder()
            validator = StrictJsonValidator()
            gemini = GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())

            ai_svc = AiAssistantService(
                db=db,
                prompt_builder=prompt_builder,
                gemini=gemini,
                validator=validator,
            )
            action_svc = EmailActionService(db=db)
            meeting_svc = MeetingService(db=db)
            reply_svc = ReplyNeedService(
                db=db,
                meeting_service=meeting_svc,
                prompt_builder=prompt_builder,
                gemini=gemini,
                validator=validator,
                config=ReplyNeedConfig(min_confidence=0.65),
            )

            ai_resp = ai_request(body=AiRequestRequest(emailId=mid, prompt="Summarize"), user_id=user_id, svc=ai_svc)
            self.assertEqual(ai_resp.emailId, mid)
            self.assertTrue(ai_resp.responseText)

            compose_resp = ai_compose(
                body=AiComposeRequest(body="Hello there", to=None, cc=None, subject=None, instruction=None),
                user_id=user_id,
                svc=ai_svc,
            )
            self.assertEqual(compose_resp.revisedText, "Hello there")
            self.assertIn(compose_resp.source, {"default", "gemini"})

            act_resp = email_actions(
                body=EmailActionRequest(emailId=mid, action="Archive"),
                user_id=user_id,
                svc=action_svc,
            )
            self.assertEqual(act_resp.status, "ok")

            with db.connect() as conn:
                n = int(conn.execute("SELECT COUNT(1) AS n FROM email_action_logs").fetchone()["n"])
            self.assertEqual(n, 1)

            meet_resp = meeting_check(messageId=mid, user_id=user_id, db=db, meeting_service=meeting_svc)
            self.assertEqual(meet_resp.messageId, mid)
            self.assertFalse(meet_resp.meetingRelated)
            self.assertEqual(meet_resp.source, "default")

            rn_resp = reply_need(body=ReplyNeedRequest(messageId=mid), user_id=user_id, svc=reply_svc)
            self.assertEqual(rn_resp.messageId, mid)
            self.assertTrue(rn_resp.label)

            with db.connect() as conn:
                n2 = int(conn.execute("SELECT COUNT(1) AS n FROM reply_need_classifications").fetchone()["n"])
            self.assertEqual(n2, 1)

            fb = reply_need_feedback(
                body=ReplyNeedFeedbackRequest(messageId=mid, userLabel="NEEDS_REPLY", comment="ok"),
                user_id=user_id,
                svc=reply_svc,
            )
            self.assertEqual(fb.status_code, 204)

            with db.connect() as conn:
                n3 = int(conn.execute("SELECT COUNT(1) AS n FROM reply_need_feedback").fetchone()["n"])
            self.assertEqual(n3, 1)

    def test_send_email_happy_path_persists_sent_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(tmp)
            user_id = "demo"
            fake_smtp = _FakeSmtp()

            from outlookplus_backend.credentials import CredentialStore
            store = CredentialStore(db=db)

            with _temp_environ(
                {
                    "OUTLOOKPLUS_SMTP_HOST": "example.com",
                    "OUTLOOKPLUS_SMTP_USERNAME": "demo@example.com",
                    "OUTLOOKPLUS_SMTP_PASSWORD": "pw",
                }
            ):
                import outlookplus_backend.api.routes as _routes_mod
                orig_fn = _routes_mod.get_smtp_for_user
                _routes_mod.get_smtp_for_user = lambda uid: fake_smtp
                try:
                    resp = send_email(
                        body=SendEmailRequest(to="a@example.com", cc=None, bcc=None, subject="Hi", body="Body"),
                        user_id=user_id,
                        db=db,
                        store=store,
                    )
                finally:
                    _routes_mod.get_smtp_for_user = orig_fn

            self.assertTrue(resp.id.startswith("sent_"))
            self.assertEqual(len(fake_smtp.sent), 1)

            with db.connect() as conn:
                repo = EmailRepositorySqlite(conn)
                sent_items = repo.list_emails(
                    user_id=user_id,
                    folder="sent",
                    label=None,
                    limit=10,
                    cursor_received_at_utc=None,
                )
            self.assertEqual(len(sent_items), 1)
            self.assertEqual(sent_items[0].mailbox_message_id, resp.id)


class WorkerIngestionHappyPathTests(unittest.TestCase):
    def test_ingestion_worker_writes_email_attachment_and_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            attachments_dir = str(Path(tmp) / "attachments")
            os.makedirs(attachments_dir, exist_ok=True)

            db = _make_db(tmp)
            user_id = "demo"

            ics = (
                "BEGIN:VCALENDAR\r\n"
                "VERSION:2.0\r\n"
                "METHOD:REQUEST\r\n"
                "BEGIN:VEVENT\r\n"
                "SUMMARY:Test Meeting\r\n"
                "DTSTART:20260308T120000Z\r\n"
                "DTEND:20260308T123000Z\r\n"
                "ORGANIZER:mailto:organizer@example.com\r\n"
                "LOCATION:Room 1\r\n"
                "END:VEVENT\r\n"
                "END:VCALENDAR\r\n"
            ).encode("utf-8")

            msg = EmailMessage()
            msg["Subject"] = "Calendar invite"
            msg["From"] = "sender@example.com"
            msg["To"] = "you@example.com"
            msg.set_content("Please see attached.")
            msg.add_attachment(ics, maintype="text", subtype="calendar", filename="invite.ics")

            raw = _FakeRawMailboxMessage(uidvalidity=123, uid=1, rfc822_bytes=msg.as_bytes())
            mailbox = _FakeMailbox(messages=[raw])

            prompt_builder = PromptBuilder()
            validator = StrictJsonValidator()
            gemini = GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())

            meeting_classifier = MeetingClassifier(
                db=db,
                prompt_builder=prompt_builder,
                gemini=gemini,
                validator=validator,
                ics_extractor=IcsExtractor(),
            )
            analysis_classifier = EmailAnalysisClassifier(
                db=db,
                prompt_builder=prompt_builder,
                gemini=gemini,
                validator=validator,
            )

            worker = IngestionWorker(
                db=db,
                mailbox=mailbox,  # type: ignore[arg-type]
                meeting_classifier=meeting_classifier,
                email_analysis_classifier=analysis_classifier,
            )

            with _temp_environ({"OUTLOOKPLUS_ATTACHMENTS_DIR": attachments_dir}):
                n = worker.run_once(user_id=user_id)

            self.assertEqual(n, 1)

            mailbox_message_id = "123:1"
            with db.connect() as conn:
                email_repo = EmailRepositorySqlite(conn)
                email = email_repo.get_email_by_message_id(user_id=user_id, mailbox_message_id=mailbox_message_id)
                self.assertIsNotNone(email)

                att_count = int(conn.execute("SELECT COUNT(1) AS n FROM attachments").fetchone()["n"])
                self.assertEqual(att_count, 1)

                analysis_count = int(conn.execute("SELECT COUNT(1) AS n FROM email_ai_analysis").fetchone()["n"])
                self.assertEqual(analysis_count, 1)

                state = conn.execute("SELECT imap_uidvalidity, last_seen_uid FROM ingestion_state WHERE user_id=?", (user_id,)).fetchone()
                self.assertIsNotNone(state)
                self.assertEqual(int(state[0]), 123)
                self.assertEqual(int(state[1]), 1)

            # Ensure attachment bytes were written to disk.
            files = list(Path(attachments_dir).rglob("*.bin"))
            self.assertTrue(files)


class ApiHttpIntegrationTests(unittest.TestCase):
    def test_http_list_emails_mode_a_demo_user(self) -> None:
        # End-to-end: FastAPI app + routing + default auth Mode A.
        from fastapi.testclient import TestClient

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "api-test.db")
            attachments_dir = str(Path(tmp) / "attachments")
            os.makedirs(attachments_dir, exist_ok=True)

            with _temp_environ(
                {
                    "OUTLOOKPLUS_DB_PATH": db_path,
                    "OUTLOOKPLUS_ATTACHMENTS_DIR": attachments_dir,
                    "OUTLOOKPLUS_AUTH_MODE": "A",
                }
            ):
                _reset_wiring_caches()
                # Ensure schema exists.
                Db(db_path=db_path).init_schema()
                _seed_one_email(db=Db(db_path=db_path), user_id="demo", mailbox_message_id="1:1")

                app = create_app()
                client = TestClient(app)
                resp = client.get("/api/emails?folder=inbox&limit=50")
                self.assertEqual(resp.status_code, 200)
                payload: dict[str, Any] = resp.json()
                self.assertEqual(len(payload.get("items") or []), 1)
                self.assertEqual(payload["items"][0]["id"], "1:1")

    def test_http_list_emails_mode_b_dev_token(self) -> None:
        # End-to-end auth dependency in Mode B.
        from fastapi.testclient import TestClient

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "api-test.db")
            attachments_dir = str(Path(tmp) / "attachments")
            os.makedirs(attachments_dir, exist_ok=True)

            with _temp_environ(
                {
                    "OUTLOOKPLUS_DB_PATH": db_path,
                    "OUTLOOKPLUS_ATTACHMENTS_DIR": attachments_dir,
                    "OUTLOOKPLUS_AUTH_MODE": "B",
                }
            ):
                _reset_wiring_caches()
                Db(db_path=db_path).init_schema()
                _seed_one_email(db=Db(db_path=db_path), user_id="alice", mailbox_message_id="1:2")

                app = create_app()
                client = TestClient(app)
                resp = client.get(
                    "/api/emails?folder=inbox&limit=50",
                    headers={"Authorization": "Bearer dev:alice"},
                )
                self.assertEqual(resp.status_code, 200)
                payload: dict[str, Any] = resp.json()
                self.assertEqual(payload["items"][0]["id"], "1:2")

    def test_http_send_email_overrides_smtp(self) -> None:
        # End-to-end send flow: request -> smtp dependency -> persistence.
        # We monkey-patch get_smtp_for_user to avoid real network calls.
        from fastapi.testclient import TestClient
        import outlookplus_backend.wiring as wiring
        import outlookplus_backend.api.routes as routes_mod

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "api-test.db")
            attachments_dir = str(Path(tmp) / "attachments")
            os.makedirs(attachments_dir, exist_ok=True)

            fake_smtp = _FakeSmtp()

            with _temp_environ(
                {
                    "OUTLOOKPLUS_DB_PATH": db_path,
                    "OUTLOOKPLUS_ATTACHMENTS_DIR": attachments_dir,
                    "OUTLOOKPLUS_AUTH_MODE": "A",
                    "OUTLOOKPLUS_SMTP_HOST": "example.com",
                    "OUTLOOKPLUS_SMTP_USERNAME": "demo@example.com",
                    "OUTLOOKPLUS_SMTP_PASSWORD": "pw",
                }
            ):
                _reset_wiring_caches()
                Db(db_path=db_path).init_schema()

                app = create_app()
                # Monkey-patch the function that send_email calls internally.
                orig_fn = routes_mod.get_smtp_for_user
                routes_mod.get_smtp_for_user = lambda uid: fake_smtp
                try:
                    client = TestClient(app)
                    resp = client.post(
                        "/api/send-email",
                        json={"to": "a@example.com", "subject": "Hi", "body": "Body"},
                    )
                    self.assertEqual(resp.status_code, 200)
                    payload: dict[str, Any] = resp.json()
                    self.assertTrue(str(payload["id"]).startswith("sent_"))
                    self.assertEqual(len(fake_smtp.sent), 1)

                    # Sent item persisted.
                    with Db(db_path=db_path).connect() as conn:
                        n = int(conn.execute("SELECT COUNT(1) AS n FROM emails WHERE folder='sent'").fetchone()["n"])
                    self.assertEqual(n, 1)
                finally:
                    routes_mod.get_smtp_for_user = orig_fn


if __name__ == "__main__":
    unittest.main()
