# Test Specification: `backend/outlookplus_backend/api/routes.py`

## File Description

Defines all REST API endpoints for the OutlookPlus backend using FastAPI's `APIRouter`. Contains utility functions for parsing email addresses and converting text to HTML, plus 11 route handlers that orchestrate email CRUD, SMTP sending, AI assistant operations, meeting classification, and reply-need classification.

## Functions

1. `_sender_from_from_addr(from_addr)`
2. `_body_to_html(body_text)`
3. `_parse_recipients(value)`
4. `list_emails(...)`
5. `get_email(...)`
6. `get_email_route(...)`
7. `patch_email(...)`
8. `send_email(...)`
9. `email_actions(...)`
10. `ai_request(...)`
11. `ai_compose(...)`
12. `meeting_check(...)`
13. `reply_need(...)`
14. `reply_need_feedback(...)`

## Test Table

| Test Name | Function Under Test | Test Purpose | Test Inputs | Expected Output |
|-----------|---------------------|--------------|-------------|-----------------|
| sender parse: full "Name \<email\>" format | `_sender_from_from_addr` | Verify name and email extracted correctly | `from_addr = "Alice Smith <alice@example.com>"` | `EmailSenderDto(name="Alice Smith", email="alice@example.com", avatar=None)` |
| sender parse: None falls back to defaults | `_sender_from_from_addr` | Cover all three fallback branches (name from local-part, name "Unknown", email default) | `from_addr = None` | `name="Unknown"`, `email="unknown@example.com"` |
| body to html: converts text with newlines to HTML | `_body_to_html` | Cover escaping, single-newline, and double-newline replacement | `body_text = "Hello <world>\n\nPara2\nLine2"` | `"<p>Hello &lt;world&gt;</p><p>Para2<br/>Line2</p>"` |
| body to html: None returns empty string | `_body_to_html` | Cover the early-return branch | `body_text = None` | `""` |
| parse recipients: multiple addresses with dedup | `_parse_recipients` | Cover parsing, dedup, and order preservation in one test | `value = "alice@a.com, Bob <bob@b.com>, Alice@A.com"` | `["alice@a.com", "bob@b.com"]` (third is duplicate) |
| list_emails: returns items with AI analysis and pagination cursor | `list_emails` | Cover happy path with folder filter and cursor logic | `folder="inbox"`, `limit=2`, mock repo returns exactly 2 emails, mock analysis_service returns analysis | `EmailListResponse` with 2 items enriched with AI analysis; `nextCursor` equals last email's `received_at_utc` |
| get_email: returns full EmailDto with body | `get_email` | Cover happy path including body_html fallback to _body_to_html | `email_id="msg-1"`, mock repo returns email with `body_html=None`, `body_text="Hello"` | `EmailDto` with `body="<p>Hello</p>"` |
| get_email: email not found raises 404 | `get_email` | Cover the None-check error branch | `email_id="nonexistent"`, mock repo returns `None` | Raises `HTTPException(status_code=404)` |
| get_email_route: delegates to get_email | `get_email_route` | Verify thin wrapper calls through correctly | `email_id="msg-1"` with valid mocks | Returns same `EmailDto` as `get_email` |
| patch_email: sets read status returns 204 | `patch_email` | Cover success path | `email_id="msg-1"`, `body=PatchEmailRequest(read=True)`, mock `set_read` returns `True` | Response with status 204 |
| patch_email: read is None raises 400 | `patch_email` | Cover validation error branch | `body=PatchEmailRequest(read=None)` | Raises `HTTPException(status_code=400)` |
| send_email: success sends via SMTP and persists to DB | `send_email` | Cover the full happy path (parse recipients, SMTP send, DB upsert) | `body=SendEmailRequest(to="a@b.com", subject="Hi", body="Hello")`, SMTP env vars set, mock smtp.send succeeds | Returns `SendEmailResponse` with id, to, subject; `smtp.send` called; email upserted to "sent" folder |
| email_actions: success returns ok | `email_actions` | Cover happy path | `body=EmailActionRequest(emailId="msg-1", action="archive")`, mock svc.execute succeeds | Returns `EmailActionResponse(status="ok")` |
| ai_request: returns AI response text | `ai_request` | Cover happy path | `body=AiRequestRequest(emailId="msg-1", prompt="Summarize")`, mock svc returns response | Returns `AiRequestResponse(responseText="Summary here")` |
| ai_compose: returns revised text | `ai_compose` | Cover happy path | `body=AiComposeRequest(body="Draft text")`, mock svc returns revised text | Returns `AiComposeResponse(revisedText="Revised", source="gemini")` |
| meeting_check: returns meeting classification | `meeting_check` | Cover happy path | `messageId="msg-1"`, mock repo returns email_id, mock meeting_service returns status | Returns `MeetingCheckResponse(meetingRelated=True, confidence=0.9, ...)` |
| reply_need: returns classification result | `reply_need` | Cover happy path | `body=ReplyNeedRequest(messageId="msg-1")`, mock svc returns result | Returns `ReplyNeedResponse` with label, confidence, reasons, source |
| reply_need_feedback: valid label returns 204 | `reply_need_feedback` | Cover success path | `body=ReplyNeedFeedbackRequest(messageId="msg-1", userLabel="NEEDS_REPLY", comment="Agree")` | Response with status 204 |
| reply_need_feedback: invalid userLabel raises 400 | `reply_need_feedback` | Cover the validation guard | `body=ReplyNeedFeedbackRequest(messageId="msg-1", userLabel="INVALID")` | Raises `HTTPException(status_code=400)` |
