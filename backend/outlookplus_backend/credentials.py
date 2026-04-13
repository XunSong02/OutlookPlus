"""Credential store – persists user-supplied IMAP / SMTP / Gemini credentials.

Credentials are stored in SQLite (same DB as emails) and fall back to
environment variables when nothing has been saved yet.  This lets the app
work both locally (`.env`) and in a Lambda / cloud deployment where the
frontend posts credentials via the REST API.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImapCredentials:
    host: str
    port: int
    username: str
    password: str
    folder: str = "INBOX"


@dataclass(frozen=True)
class SmtpCredentials:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class GeminiCredentials:
    api_key: str
    model: str = "gemini-3-flash-preview"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

_CREDENTIALS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_credentials (
    user_id TEXT NOT NULL,
    cred_type TEXT NOT NULL,         -- 'imap' | 'smtp' | 'gemini'
    payload_json TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (user_id, cred_type)
);
"""


class CredentialStore:
    """Read / write credentials with SQLite persistence + env-var fallback."""

    def __init__(self, db) -> None:
        # db is outlookplus_backend.persistence.db.Db
        self._db = db
        self._ensure_table()

    # -- bootstrap --------------------------------------------------------

    def _ensure_table(self) -> None:
        with self._db.connect() as conn:
            conn.executescript(_CREDENTIALS_TABLE_SQL)

    # -- write ------------------------------------------------------------

    def save(self, *, user_id: str, cred_type: str, payload: dict[str, Any]) -> None:
        from outlookplus_backend.utils.time import now_utc_rfc3339

        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_credentials (user_id, cred_type, payload_json, updated_at_utc)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, cred_type) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (user_id, cred_type, json.dumps(payload), now_utc_rfc3339()),
            )
            conn.commit()

    def delete(self, *, user_id: str, cred_type: str | None = None) -> None:
        with self._db.connect() as conn:
            if cred_type:
                conn.execute(
                    "DELETE FROM user_credentials WHERE user_id = ? AND cred_type = ?",
                    (user_id, cred_type),
                )
            else:
                conn.execute("DELETE FROM user_credentials WHERE user_id = ?", (user_id,))
            conn.commit()

    # -- read -------------------------------------------------------------

    def _get_raw(self, *, user_id: str, cred_type: str) -> dict[str, Any] | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM user_credentials WHERE user_id = ? AND cred_type = ?",
                (user_id, cred_type),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    # -- typed accessors (DB first → env fallback) -------------------------

    def get_imap(self, *, user_id: str) -> ImapCredentials | None:
        raw = self._get_raw(user_id=user_id, cred_type="imap")
        if raw:
            return ImapCredentials(
                host=raw["host"],
                port=int(raw.get("port", 993)),
                username=raw["username"],
                password=raw["password"],
                folder=raw.get("folder", "INBOX"),
            )
        # Fallback to env
        host = os.getenv("OUTLOOKPLUS_IMAP_HOST")
        username = os.getenv("OUTLOOKPLUS_IMAP_USERNAME")
        password = os.getenv("OUTLOOKPLUS_IMAP_PASSWORD")
        if host and username and password:
            return ImapCredentials(
                host=host,
                port=int(os.getenv("OUTLOOKPLUS_IMAP_PORT", "993")),
                username=username,
                password=password,
                folder=os.getenv("OUTLOOKPLUS_IMAP_FOLDER", "INBOX"),
            )
        return None

    def get_smtp(self, *, user_id: str) -> SmtpCredentials | None:
        raw = self._get_raw(user_id=user_id, cred_type="smtp")
        if raw:
            return SmtpCredentials(
                host=raw["host"],
                port=int(raw.get("port", 587)),
                username=raw["username"],
                password=raw["password"],
            )
        # Fallback to env
        host = os.getenv("OUTLOOKPLUS_SMTP_HOST")
        username = os.getenv("OUTLOOKPLUS_SMTP_USERNAME")
        password = os.getenv("OUTLOOKPLUS_SMTP_PASSWORD")
        if host and username and password:
            return SmtpCredentials(
                host=host,
                port=int(os.getenv("OUTLOOKPLUS_SMTP_PORT", "587")),
                username=username,
                password=password,
            )
        return None

    def get_gemini(self, *, user_id: str) -> GeminiCredentials | None:
        raw = self._get_raw(user_id=user_id, cred_type="gemini")
        if raw:
            return GeminiCredentials(
                api_key=raw["api_key"],
                model=raw.get("model", "gemini-3-flash-preview"),
            )
        # Fallback to env
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or (os.getenv("OUTLOOKPLUS_GEMINI_API_KEY") or "").strip()
        if api_key:
            return GeminiCredentials(
                api_key=api_key,
                model=os.getenv("OUTLOOKPLUS_GEMINI_MODEL", "gemini-3-flash-preview"),
            )
        return None

    def get_status(self, *, user_id: str) -> dict[str, bool]:
        """Return which credential types are configured (DB or env)."""
        return {
            "imap": self.get_imap(user_id=user_id) is not None,
            "smtp": self.get_smtp(user_id=user_id) is not None,
            "gemini": self.get_gemini(user_id=user_id) is not None,
        }
