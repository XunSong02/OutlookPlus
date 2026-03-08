from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from outlookplus_backend.persistence.schema import SCHEMA_SQL, apply_migrations


class _ClosingConnection(sqlite3.Connection):
    """SQLite Connection that closes when used as a context manager.

    Python's default sqlite3.Connection context manager commits/rolls back but
    does not close the connection. This backend commonly uses
    `with db.connect() as conn:` and expects resources to be released.
    """

    def __exit__(self, exc_type, exc, tb):  # type: ignore[override]
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            try:
                self.close()
            except Exception:
                pass


@dataclass(frozen=True)
class Db:
    db_path: str

    def connect(self) -> sqlite3.Connection:
        Path(os.path.dirname(self.db_path) or ".").mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
            factory=_ClosingConnection,
        )
        conn.row_factory = sqlite3.Row
        # Apply pragmas per-connection.
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            apply_migrations(conn)
