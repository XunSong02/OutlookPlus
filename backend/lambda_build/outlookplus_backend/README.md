# outlookplus_backend (source code guide for SRE)

This directory is the Python package that implements the OutlookPlus backend.

It is designed to run as two separate runtimes from the same code:

- API runtime: [../run_api.py](../run_api.py)
- Worker runtime: [../run_worker.py](../run_worker.py)

## What this package depends on

### Python / stdlib

The majority of integrations are implemented using Python’s standard library:

- SQLite access: `sqlite3`
- IMAP (worker): `imaplib`
- SMTP (send mail): `smtplib`
- HTTPS client (Gemini): `urllib.request`
- MIME parsing (worker): `email.*`
- Filesystem: `pathlib`, `os`

### Required third-party libraries

Installed via [../requirements.txt](../requirements.txt):

- FastAPI: request routing, dependency injection, and response handling
- Uvicorn: ASGI server used by the API runtime
- Pydantic v2: request/response DTO validation

### Optional external services

These are not Python dependencies, but the runtime can optionally call them:

- IMAP server (worker ingestion)
- SMTP server (send mail)
- Gemini API (LLM-backed classifications and AI assistant responses)

## Storage (what this code creates/reads/writes)

### SQLite database (primary state store)

- Default: `data/outlookplus.db` (config: `OUTLOOKPLUS_DB_PATH`)
- Created and migrated by: `outlookplus_backend.persistence.db.Db.init_schema()`

The code creates/reads/writes the following tables:

- `emails` (feed/detail fields + UI state: folder/read/labels)
- `attachments` (metadata + on-disk path)
- `email_ai_analysis` (category/sentiment/summary/suggestedActions)
- `ai_requests` (custom AI requests log)
- `email_action_logs` (suggested-action click log)
- `meeting_classifications` (meeting-related status)
- `reply_need_classifications` (needs-reply classifier cache)
- `reply_need_feedback` (human feedback)
- `ingestion_state` (IMAP cursor: UIDVALIDITY + last_seen_uid)

### Filesystem (attachment bytes)

- Base directory: `data/attachments/` (config: `OUTLOOKPLUS_ATTACHMENTS_DIR`)
- Writer: `outlookplus_backend.persistence.file_store.AttachmentFileStore`
- Current scope: only `text/calendar` attachments are persisted by the worker.

## Module-by-module dependencies (external tech/services)

### API layer: `outlookplus_backend.api`

Files:

- `api/app.py`: creates the FastAPI app and configures CORS.
- `api/routes.py`: defines the REST API under the `/api` prefix.
- `api/models.py`: Pydantic request/response DTOs.

Dependencies:

- Framework: FastAPI
- DTO validation: Pydantic
- Storage: SQLite via `persistence.Db`
- External services (optional / endpoint-specific):
  - SMTP for `POST /api/send-email`
  - Gemini for `/api/ai/*`, `/api/reply-need`, `/api/meeting/check` (best-effort)

Databases touched:

- Reads/writes `emails` (list/detail/patch)
- Reads `email_ai_analysis` (inline `aiAnalysis`)
- Writes `email_action_logs` (`POST /api/email-actions`)
- Writes `ai_requests` (`POST /api/ai/request`)
- Reads `meeting_classifications` (`GET /api/meeting/check`)
- Reads/writes `reply_need_classifications` and `reply_need_feedback` (`/api/reply-need*`)

### Auth: `outlookplus_backend.auth`

Dependencies:

- FastAPI dependency injection (`Depends`, `Header`)

External services:

- None (Mode C / real verification is not implemented).

Databases touched:

- None.

### Persistence: `outlookplus_backend.persistence`

Files:

- `persistence/schema.py`: DDL for all tables.
- `persistence/db.py`: SQLite connection factory with WAL + foreign keys.
- `persistence/unit_of_work.py`: transaction scoping used by the worker.
- `persistence/repos.py`: SQLite repositories.
- `persistence/file_store.py`: attachment writes with interprocess file locking.

Dependencies:

- Technology: SQLite (file-based)
- OS filesystem (attachments)

External services:

- None.

Databases touched:

- Creates all tables listed in the Storage section.

### LLM utilities + provider client: `outlookplus_backend.llm`

Files:

- `llm/prompts.py`: prompt builders (strict JSON contracts)
- `llm/validator.py`: strict JSON validators for each feature
- `llm/throttle.py`: rate limiting and retry policy
- `llm/gemini.py`: Gemini HTTPS client (stdlib `urllib`)

Dependencies:

- External service (optional): Gemini API

Databases touched:

- None directly (services persist outcomes).

### AI assistant: `outlookplus_backend.ai_assistant`

Dependencies:

- Optional external service: Gemini API
- Storage: writes `ai_requests` (best-effort logging)

Databases touched:

- Reads `emails`
- Writes `ai_requests`

### Email analysis: `outlookplus_backend.email_analysis`

Dependencies:

- Optional external service: Gemini API
- Storage: reads/writes `email_ai_analysis`

Databases touched:

- Reads `emails`
- Reads/writes `email_ai_analysis`

### Email actions: `outlookplus_backend.email_actions`

Dependencies:

- None beyond SQLite

Databases touched:

- Reads `emails`
- Writes `email_action_logs`

### Worker ingestion: `outlookplus_backend.worker` + `outlookplus_backend.imap`

Dependencies:

- External service (optional but required for ingestion to function): IMAP server
- stdlib tech: `imaplib` (IMAPS), `email.*` parsing
- Storage: reads/writes SQLite; writes attachment bytes

Databases touched:

- Reads/writes `emails`
- Reads/writes `attachments`
- Reads/writes `ingestion_state`
- Triggers and persists:
  - `meeting_classifications` (best-effort)
  - `email_ai_analysis` (always persisted once per email with fallback)

### SMTP client: `outlookplus_backend.smtp`

Dependencies:

- External service (optional): SMTP submission server
- stdlib tech: `smtplib`

Databases touched:

- None (the API handler writes a synthetic “sent” email to `emails`).

### ICS parsing: `outlookplus_backend.ics`

Dependencies:

- None (pure parsing)

Databases touched:

- None.

### Meeting: `outlookplus_backend.meeting`

Dependencies:

- Optional external service: Gemini API
- Optional input: ICS file stored on disk (from `attachments` rows)

Databases touched:

- Reads `emails`
- Reads `attachments`
- Reads/writes `meeting_classifications`

### Reply-need: `outlookplus_backend.reply_need`

Dependencies:

- Optional external service: Gemini API
- Reads meeting signal from SQLite via `MeetingService`

Databases touched:

- Reads `emails`
- Reads/writes `reply_need_classifications`
- Writes `reply_need_feedback`
- Reads `meeting_classifications`

## Operational notes for SRE

- Schema creation is automatic on process start; there is no separate migration tool.
- All logs are printed to stdout/stderr.
- CORS is permissive by default (dev/demo).
