from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from outlookplus_backend.persistence.db import Db


@dataclass
class SqliteUnitOfWork:
    db: Db

    conn: sqlite3.Connection | None = None

    def __enter__(self) -> "SqliteUnitOfWork":
        self.conn = self.db.connect()
        self.conn.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self.conn is not None
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()

    def cursor(self) -> sqlite3.Connection:
        assert self.conn is not None
        return self.conn
