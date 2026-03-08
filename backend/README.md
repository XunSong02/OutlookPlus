# OutlookPlus Backend (FastAPI + Worker)

This folder contains the backend implementation described in:
- `backend_specification_Architecture.md`
- `backend_specification_Modules.md`

It runs as **two runtimes** from the same code:
- API runtime (FastAPI)
- Ingestion worker runtime (IMAP + meeting classification)

## Install

From this folder:

```bash
pip install -r requirements.txt
```

## Run API

Quick config (recommended):
- Copy `.env.example` to `.env` in this folder, then fill in values.
- You can run API without IMAP/Gemini keys; those features will degrade gracefully.

```bash
python run_api.py
```

Dev auth (MVP stub):
- Send `Authorization: Bearer dev:<userId>`

Example:
- `Authorization: Bearer dev:alice`

## Run Worker

Worker config lives in the same `.env` file (copy from `.env.example`).

Set a user id for the worker loop:

- `OUTLOOKPLUS_WORKER_USER_ID=alice`

Then run:

```bash
python run_worker.py
```

## Storage

Defaults:
- SQLite DB: `data/outlookplus.db` (WAL enabled)
- Attachments: `data/attachments/`

Override with:
- `OUTLOOKPLUS_DB_PATH`
- `OUTLOOKPLUS_ATTACHMENTS_DIR`

## IMAP (Worker ingestion)

Worker reads IMAP settings from env vars:
- `OUTLOOKPLUS_IMAP_HOST`
- `OUTLOOKPLUS_IMAP_PORT` (default: `993`)
- `OUTLOOKPLUS_IMAP_USERNAME`
- `OUTLOOKPLUS_IMAP_PASSWORD`
- `OUTLOOKPLUS_IMAP_FOLDER` (default: `INBOX`)

If these are not set, ingestion returns 0 messages.

## Gemini (Meeting + Reply-Need)

Gemini calls are server-side only. The backend reads the API key from the process environment (optionally via a local `.env` if you use a dotenv loader). Env vars:
- `GEMINI_API_KEY` (required to call Gemini)
# set GEMINI_API_KEY=API key
- `OUTLOOKPLUS_GEMINI_MODEL` (default: `gemini-3-flash-preview`)


Reply-need deterministic fallback:
- `REPLY_NEED_MIN_CONFIDENCE` (default: `0.65`)

If Gemini is not configured or fails, reply-need returns `label="UNSURE"`.
