from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS emails (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            TEXT NOT NULL,
    mailbox_message_id TEXT NOT NULL,

    folder             TEXT NOT NULL DEFAULT 'inbox',
    is_read            INTEGER NOT NULL DEFAULT 0,
    labels_json        TEXT NOT NULL DEFAULT '[]',

    subject            TEXT,
    from_addr          TEXT,
    to_addrs           TEXT,
    cc_addrs           TEXT,
    sent_at_utc        TEXT,
    received_at_utc    TEXT NOT NULL,

    preview_text       TEXT,
    body_text          TEXT,
    body_html          TEXT,

    created_at_utc     TEXT NOT NULL,

    UNIQUE(user_id, mailbox_message_id)
);

CREATE INDEX IF NOT EXISTS idx_emails_user_received ON emails(user_id, received_at_utc);

CREATE TABLE IF NOT EXISTS email_ai_analysis (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                TEXT NOT NULL,
    email_id               INTEGER NOT NULL,

    category               TEXT NOT NULL,
    sentiment              TEXT NOT NULL,
    summary                TEXT NOT NULL,
    suggested_actions_json TEXT NOT NULL,
    source                 TEXT NOT NULL,
    created_at_utc         TEXT NOT NULL,

    UNIQUE(user_id, email_id),
    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_ai_analysis_email ON email_ai_analysis(email_id);

CREATE TABLE IF NOT EXISTS ai_requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    email_id       INTEGER NOT NULL,
    prompt_text    TEXT NOT NULL,
    response_text  TEXT NOT NULL,
    source         TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,

    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_requests_email ON ai_requests(email_id);

CREATE TABLE IF NOT EXISTS email_action_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    email_id       INTEGER NOT NULL,
    action         TEXT NOT NULL,
    status         TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,

    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_action_logs_email ON email_action_logs(email_id);

CREATE TABLE IF NOT EXISTS attachments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    email_id       INTEGER NOT NULL,
    filename       TEXT,
    content_type   TEXT NOT NULL,
    size_bytes     INTEGER,
    storage_path   TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,

    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attachments_email ON attachments(email_id);

CREATE TABLE IF NOT EXISTS meeting_classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    email_id        INTEGER NOT NULL,

    meeting_related INTEGER NOT NULL CHECK(meeting_related IN (0, 1)),
    confidence      REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    rationale       TEXT,
    source          TEXT NOT NULL,
    created_at_utc  TEXT NOT NULL,

    UNIQUE(user_id, email_id),
    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_meeting_email ON meeting_classifications(email_id);

CREATE TABLE IF NOT EXISTS reply_need_classifications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    email_id       INTEGER NOT NULL,

    label          TEXT NOT NULL CHECK(label IN ('NEEDS_REPLY', 'NO_REPLY_NEEDED', 'UNSURE')),
    confidence     REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    reasons_json   TEXT NOT NULL,
    source         TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,

    UNIQUE(user_id, email_id),
    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reply_need_email ON reply_need_classifications(email_id);

CREATE TABLE IF NOT EXISTS reply_need_feedback (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           TEXT NOT NULL,
    email_id          INTEGER NOT NULL,
    classification_id INTEGER,

    user_label        TEXT NOT NULL CHECK(user_label IN ('NEEDS_REPLY', 'NO_REPLY_NEEDED')),
    comment           TEXT,
    created_at_utc    TEXT NOT NULL,

    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE,
    FOREIGN KEY(classification_id) REFERENCES reply_need_classifications(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_email ON reply_need_feedback(email_id);

CREATE TABLE IF NOT EXISTS ingestion_state (
    user_id          TEXT PRIMARY KEY,
    imap_uidvalidity INTEGER NOT NULL,
    last_seen_uid    INTEGER NOT NULL,
    updated_at_utc   TEXT NOT NULL
);

"""


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(r[1]) == column for r in rows)


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Best-effort schema migrations for developer SQLite DBs.

    `CREATE TABLE IF NOT EXISTS` does not add new columns to an existing table,
    so we patch missing columns here to keep older DB files working.
    """

    # emails: UI-required state.
    if not _has_column(conn, "emails", "folder"):
        conn.execute("ALTER TABLE emails ADD COLUMN folder TEXT NOT NULL DEFAULT 'inbox'")
    if not _has_column(conn, "emails", "is_read"):
        conn.execute("ALTER TABLE emails ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
    if not _has_column(conn, "emails", "labels_json"):
        conn.execute("ALTER TABLE emails ADD COLUMN labels_json TEXT NOT NULL DEFAULT '[]'")
    if not _has_column(conn, "emails", "preview_text"):
        conn.execute("ALTER TABLE emails ADD COLUMN preview_text TEXT")
    if not _has_column(conn, "emails", "body_html"):
        conn.execute("ALTER TABLE emails ADD COLUMN body_html TEXT")

    # Indexes may be missing on older DBs.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_emails_user_folder_received ON emails(user_id, folder, received_at_utc)"
    )

