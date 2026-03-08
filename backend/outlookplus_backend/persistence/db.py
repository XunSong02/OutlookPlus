from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from outlookplus_backend.persistence.schema import SCHEMA_SQL, apply_migrations


@dataclass(frozen=True)
class Db:
    db_path: str

    def connect(self) -> sqlite3.Connection:
        Path(os.path.dirname(self.db_path) or ".").mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Apply pragmas per-connection.
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            apply_migrations(conn)
