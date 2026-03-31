# Test Specification: `backend/outlookplus_backend/persistence/repos.py`

## File Description

Complete data access layer for the OutlookPlus backend. Contains 8 SQLite-backed repository classes plus one standalone helper function, covering email CRUD, attachment storage, meeting classification, reply-need classification, IMAP ingestion state, AI email analysis caching, AI request logging, and email action logging.

## Functions

1. `_parse_labels(labels_json)`
2. `EmailRepositorySqlite.upsert_email(...)`
3. `EmailRepositorySqlite.list_emails(...)`
4. `EmailRepositorySqlite.get_email(...)`
5. `EmailRepositorySqlite.get_email_id_by_message_id(...)`
6. `EmailRepositorySqlite.get_email_by_message_id(...)`
7. `EmailRepositorySqlite.set_read(...)`
8. `AttachmentRepositorySqlite.add_attachment(...)`
9. `AttachmentRepositorySqlite.list_attachments(...)`
10. `AttachmentRepositorySqlite.get_first_attachment_path_by_type(...)`
11. `MeetingRepositorySqlite.get_status(...)`
12. `MeetingRepositorySqlite.upsert(...)`
13. `ReplyNeedRepositorySqlite.get(...)`
14. `ReplyNeedRepositorySqlite.upsert(...)`
15. `ReplyNeedRepositorySqlite.add_feedback(...)`
16. `IngestionStateRepositorySqlite.get_state(...)`
17. `IngestionStateRepositorySqlite.set_state(...)`
18. `EmailAnalysisRepositorySqlite.get_by_email_id(...)`
19. `EmailAnalysisRepositorySqlite.get_by_email_ids(...)`
20. `EmailAnalysisRepositorySqlite.upsert_analysis(...)`
21. `AiRequestRepositorySqlite.add_request(...)`
22. `EmailActionRepositorySqlite.add_action_log(...)`

## Test Table

| Test Name | Function Under Test | Test Purpose | Test Inputs | Expected Output |
|-----------|---------------------|--------------|-------------|-----------------|
| parse_labels: valid JSON array of strings | `_parse_labels` | Cover happy-path parsing | `labels_json = '["Work", "Urgent"]'` | `["Work", "Urgent"]` |
| parse_labels: None returns empty list | `_parse_labels` | Cover the None-guard early return | `labels_json = None` | `[]` |
| upsert_email: insert and retrieve new email | `EmailRepositorySqlite.upsert_email` | Verify insertion returns id and data is persisted | `user_id="user1"`, `mailbox_message_id="msg-1"`, `email=ParsedEmail(subject="Test", ...)`, `folder="inbox"`, `labels=["Work"]` | Returns `id > 0`; subsequent `get_email_by_message_id("msg-1")` returns email with `folder="inbox"`, `labels=["Work"]` |
| list_emails: filters by folder and respects limit and order | `EmailRepositorySqlite.list_emails` | Cover folder filter, limit, and DESC ordering | Insert 3 emails (2 in "inbox", 1 in "sent") with different dates. Query `folder="inbox"`, `limit=10` | Returns 2 emails, both `folder="inbox"`, ordered by `received_at_utc` DESC |
| get_email: found returns EmailMessage | `EmailRepositorySqlite.get_email` | Cover the found path | Insert email, get `id`, call `get_email(email_id=id)` | Returns `EmailMessage` with matching fields |
| get_email_id_by_message_id: found returns id | `EmailRepositorySqlite.get_email_id_by_message_id` | Cover the found path | Insert email with `mailbox_message_id="msg-1"` | Returns the integer `id` |
| get_email_by_message_id: found returns full EmailMessage | `EmailRepositorySqlite.get_email_by_message_id` | Cover the found path | Insert email with `mailbox_message_id="msg-1"` | Returns `EmailMessage` with all fields populated |
| set_read: marks email as read and returns True | `EmailRepositorySqlite.set_read` | Cover the success path (rowcount > 0) | Insert email with `is_read=False`, call `set_read(read=True)` | Returns `True`; subsequent get shows `is_read=True` |
| set_read: nonexistent email returns False | `EmailRepositorySqlite.set_read` | Cover the not-found branch (rowcount == 0) | `mailbox_message_id="nonexistent"` | Returns `False` |
| add_attachment: inserts and returns id | `AttachmentRepositorySqlite.add_attachment` | Verify insertion | `email_id=1`, `meta=ParsedAttachment(filename="doc.pdf", content_type="application/pdf", size_bytes=1024)`, `storage_path="/files/doc.pdf"` | Returns `id > 0` |
| list_attachments: returns all for email ordered by id | `AttachmentRepositorySqlite.list_attachments` | Verify retrieval and ordering | Insert 2 attachments for `email_id=1` | Returns list of 2 `AttachmentMeta` objects ordered by id ASC |
| get_first_attachment_path_by_type: found returns path | `AttachmentRepositorySqlite.get_first_attachment_path_by_type` | Cover the found path | Insert attachment with `content_type="text/calendar"`, `storage_path="/files/cal.ics"` | Returns `"/files/cal.ics"` |
| meeting get_status: upsert then retrieve | `MeetingRepositorySqlite.get_status` | Cover the found path via upsert + get round-trip | Upsert `meeting_related=True, confidence=0.95, rationale="Has date", source="gemini"` | `get_status` returns `MeetingStatus(meeting_related=True, confidence=0.95, ...)` |
| meeting upsert: insert new classification | `MeetingRepositorySqlite.upsert` | Verify insertion persists | `email_id=1, meeting_related=True, confidence=0.9, source="gemini"` | Subsequent `get_status` returns matching `MeetingStatus` |
| reply_need get: upsert then retrieve | `ReplyNeedRepositorySqlite.get` | Cover the found path | Upsert a classification, then call `get` | Returns `(id, ReplyNeedResult(...))` tuple |
| reply_need upsert: insert and return id | `ReplyNeedRepositorySqlite.upsert` | Verify insertion returns id | `result=ReplyNeedResult(label="NEEDS_REPLY", confidence=0.85, reasons=["Direct question"], source="gemini")` | Returns `id > 0` |
| reply_need add_feedback: inserts feedback record | `ReplyNeedRepositorySqlite.add_feedback` | Verify insertion succeeds | `email_id=1, classification_id=1, user_label="NEEDS_REPLY", comment="Agree"` | No exception raised |
| ingestion get_state: set then retrieve | `IngestionStateRepositorySqlite.get_state` | Cover the found path via set + get round-trip | `set_state(uidvalidity=100, last_seen_uid=500)`, then `get_state` | Returns `(100, 500)` |
| ingestion set_state: insert new state | `IngestionStateRepositorySqlite.set_state` | Verify upsert persistence | `user_id="user1", uidvalidity=100, last_seen_uid=500` | `get_state` returns `(100, 500)` |
| analysis get_by_email_id: upsert then retrieve | `EmailAnalysisRepositorySqlite.get_by_email_id` | Cover the found path including JSON parsing | Upsert analysis with `category="Work", sentiment="positive", summary="Good", suggested_actions=[{"kind":"suggestion","text":"Archive"}]` | Returns dict with matching fields and `suggestedActions` as list |
| analysis get_by_email_ids: batch retrieval | `EmailAnalysisRepositorySqlite.get_by_email_ids` | Cover multi-ID lookup and empty-list short-circuit | Upsert analysis for email_ids 1 and 2, query for `[1, 2]` | Returns dict with keys 1 and 2; calling with `[]` returns `{}` |
| analysis upsert: insert new analysis | `EmailAnalysisRepositorySqlite.upsert_analysis` | Verify insertion persists | `email_id=1, category="Work", sentiment="positive", summary="Good", suggested_actions=[], source="gemini"` | `get_by_email_id` returns matching dict |
| ai_request add_request: inserts and returns id | `AiRequestRepositorySqlite.add_request` | Verify insertion | `email_id=1, prompt_text="Summarize", response_text="Summary", source="gemini"` | Returns `id > 0` |
| action_log add_action_log: inserts and returns id | `EmailActionRepositorySqlite.add_action_log` | Verify insertion | `email_id=1, action="archive", status="ok"` | Returns `id > 0` |
