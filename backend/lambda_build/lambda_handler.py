"""
AWS Lambda entry point for the OutlookPlus backend.

Wraps the FastAPI app with Mangum so API Gateway events are translated
into ASGI requests that FastAPI understands.

Lambda handler string (set in AWS console):  lambda_handler.handler

Environment variables to set in the Lambda console:
  OUTLOOKPLUS_DB_PATH           /tmp/data/outlookplus.db
  OUTLOOKPLUS_ATTACHMENTS_DIR   /tmp/data/attachments
  OUTLOOKPLUS_AUTH_MODE         A        (or B for dev-token auth)

Optional (users can also set these via the Settings page):
  GEMINI_API_KEY                your-key
  OUTLOOKPLUS_GEMINI_MODEL      gemini-1.5-flash
  OUTLOOKPLUS_IMAP_HOST         imap.gmail.com
  OUTLOOKPLUS_IMAP_USERNAME     you@gmail.com
  OUTLOOKPLUS_IMAP_PASSWORD     app-password
  OUTLOOKPLUS_SMTP_HOST         smtp.gmail.com
  OUTLOOKPLUS_SMTP_USERNAME     you@gmail.com
  OUTLOOKPLUS_SMTP_PASSWORD     app-password
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Lambda writes only to /tmp.  Set sensible defaults BEFORE any app imports
# so that the DB and attachments land in a writable location.
# ---------------------------------------------------------------------------
os.environ.setdefault("OUTLOOKPLUS_DB_PATH", "/tmp/data/outlookplus.db")
os.environ.setdefault("OUTLOOKPLUS_ATTACHMENTS_DIR", "/tmp/data/attachments")
os.environ.setdefault("OUTLOOKPLUS_AUTH_MODE", "A")

# ---------------------------------------------------------------------------
# Create the FastAPI app (runs once per cold start, then cached).
# ---------------------------------------------------------------------------
from outlookplus_backend.api.app import create_app  # noqa: E402

app = create_app()

# ---------------------------------------------------------------------------
# Mangum bridges API Gateway ↔ ASGI.
# ---------------------------------------------------------------------------
try:
    from mangum import Mangum
except ImportError:
    raise ImportError(
        "mangum is required for Lambda deployment.  "
        "Run:  pip install mangum   (already in requirements.txt)"
    )

handler = Mangum(app, lifespan="off")
