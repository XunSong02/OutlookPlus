# OutlookPlus Backend (SRE Runbook)

This folder contains a small Python backend that runs as two processes from the same codebase:

- API runtime (FastAPI + Uvicorn)
- Optional ingestion worker runtime (IMAP ingestion + offline classifications)

Specs (design docs):

- [backend_specification_Architecture.md](backend_specification_Architecture.md)
- [backend_specification_Modules.md](backend_specification_Modules.md)

Source code (module-by-module dependencies + storage map):

- [outlookplus_backend/README.md](outlookplus_backend/README.md)

## External dependencies

### Required (to run the API)

- Python 3.10+ (code uses PEP 604 unions like `str | None`)
- Pip packages in [requirements.txt](requirements.txt)
	- FastAPI (HTTP framework)
	- Uvicorn (ASGI server)
	- Pydantic v2 (request/response models)
- SQLite (via Python stdlib `sqlite3`; no external DB server)
- Local filesystem access (for the SQLite file and attachment storage)

- IMAP4 over TLS (worker ingestion) via Python stdlib `imaplib`
- SMTP submission (outbound email) via Python stdlib `smtplib`
- Google Gemini API (LLM features) via HTTPS using Python stdlib `urllib` (Vertex AI Platform)

## Data storage

### SQLite database

- Default path: `data/outlookplus.db`
- Config override: `OUTLOOKPLUS_DB_PATH`
- Journal mode: WAL (set on every connection)
- Schema is created at startup (and a small best-effort migration step is applied for older dev DB files).

Tables created by this backend include:

- `emails`
- `attachments`
- `email_ai_analysis`
- `ai_requests`
- `email_action_logs`
- `meeting_classifications`
- `reply_need_classifications`
- `reply_need_feedback`
- `ingestion_state`

### Attachment files

- Default directory: `data/attachments/`
- Config override: `OUTLOOKPLUS_ATTACHMENTS_DIR`
- Only `text/calendar` attachments are stored by the worker (written atomically under an interprocess file lock).

## Configuration

Both `run_api.py` and `run_worker.py` load environment variables from a local `.env` file in this folder (if present), using a minimal built-in dotenv loader.

Common env vars:

- `OUTLOOKPLUS_DB_PATH` (default: `data/outlookplus.db`)
- `OUTLOOKPLUS_ATTACHMENTS_DIR` (default: `data/attachments`)
- `OUTLOOKPLUS_AUTH_MODE`:
	- `A` = demo (no auth, all requests use `user_id="demo"`)
	- `B` = dev stub (requires Authorization header)
- `OUTLOOKPLUS_API_HOST` (default: `127.0.0.1`)
- `OUTLOOKPLUS_API_PORT` (default: `8000`)

Dev-stub auth env vars (only relevant when `OUTLOOKPLUS_AUTH_MODE=B`):

- `OUTLOOKPLUS_DEV_TOKEN` (optional)
- `OUTLOOKPLUS_DEV_USER_ID` (required if you use `OUTLOOKPLUS_DEV_TOKEN`)

## Install

From this folder:

```bash
pip install -r requirements.txt
```

## Start

### Start API

```bash
python run_api.py
```

Auth behavior:

- Mode A (`OUTLOOKPLUS_AUTH_MODE=A`): no `Authorization` header required.
- Mode B (`OUTLOOKPLUS_AUTH_MODE=B`): send one of:
	- `Authorization: Bearer dev:<userId>`
	- OR `Authorization: Bearer <OUTLOOKPLUS_DEV_TOKEN>` (maps to `OUTLOOKPLUS_DEV_USER_ID`)

### Start worker

Worker env vars:

- `OUTLOOKPLUS_WORKER_USER_ID` (required; e.g. `alice`)
- `OUTLOOKPLUS_WORKER_POLL_SECONDS` (default: `15`)

IMAP env vars (required for ingestion to work):

- `OUTLOOKPLUS_IMAP_HOST`
- `OUTLOOKPLUS_IMAP_PORT` (default: `993`)
- `OUTLOOKPLUS_IMAP_USERNAME`
- `OUTLOOKPLUS_IMAP_PASSWORD`
- `OUTLOOKPLUS_IMAP_FOLDER` (default: `INBOX`)

Run:

```bash
python run_worker.py
```

If IMAP env vars are missing/invalid, the worker logs an IMAP error and sleeps/retries; it does not ingest.

## Stop

- API: press Ctrl+C in the API terminal
- Worker: press Ctrl+C in the worker terminal

There is no background daemon/service wrapper included in this repo.

## Reset (wipe local data)

1. Stop API + worker.
2. Delete the SQLite DB file at `OUTLOOKPLUS_DB_PATH` (default: `data/outlookplus.db`).
3. Delete the attachment directory at `OUTLOOKPLUS_ATTACHMENTS_DIR` (default: `data/attachments/`).

On the next start, the API will recreate the schema automatically.

## integrations

### SMTP

The API endpoint `POST /api/send-email` returns HTTP 400 unless SMTP is configured.

Env vars:

- `OUTLOOKPLUS_SMTP_HOST`
- `OUTLOOKPLUS_SMTP_PORT` (default: `587`)
- `OUTLOOKPLUS_SMTP_USERNAME`
- `OUTLOOKPLUS_SMTP_PASSWORD`

### Gemini

Env vars:

- `GEMINI_API_KEY` or `OUTLOOKPLUS_GEMINI_API_KEY`
- `OUTLOOKPLUS_GEMINI_MODEL`
- `OUTLOOKPLUS_GEMINI_ENDPOINT` (optional; defaults to Google Generative Language API URL)
- `REPLY_NEED_MIN_CONFIDENCE` (default: `0.65`)

Fallback behavior:

- Email AI analysis is persisted once per email; if Gemini fails, deterministic defaults are stored (`category="Work"`, `sentiment="neutral"`, etc.).
- AI assistant request/compose returns a deterministic “default” response if Gemini fails.
- Meeting classification is best-effort; if Gemini fails, no row is stored and API returns defaults.

## Observability / operations notes

- Logs: stdout/stderr only.
- Health endpoint: not implemented.
- CORS: configured permissively (`allow_origins=["*"]`) for dev/demo.
