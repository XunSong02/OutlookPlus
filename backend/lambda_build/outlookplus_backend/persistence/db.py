from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from outlookplus_backend.persistence.schema import SCHEMA_SQL, apply_migrations


# ---------------------------------------------------------------------------
# S3 helpers – only used when OUTLOOKPLUS_S3_BUCKET is set (i.e. on Lambda).
# ---------------------------------------------------------------------------
_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client("s3")
    return _s3_client


def _s3_bucket() -> str | None:
    return os.environ.get("OUTLOOKPLUS_S3_BUCKET")


def _s3_key(db_path: str) -> str:
    return "outlookplus.db"


def _download_from_s3(db_path: str) -> None:
    """Download DB from S3 to local path if it exists."""
    bucket = _s3_bucket()
    if not bucket:
        return
    Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)
    try:
        _get_s3().download_file(bucket, _s3_key(db_path), db_path)
    except _get_s3().exceptions.ClientError:
        pass  # First run – no DB in S3 yet, that's fine.


def _upload_to_s3(db_path: str) -> None:
    """Upload local DB to S3."""
    bucket = _s3_bucket()
    if not bucket:
        return
    if os.path.exists(db_path):
        _get_s3().upload_file(db_path, bucket, _s3_key(db_path))


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
    _restored: bool = False

    def _ensure_restored(self) -> None:
        """On first access, pull the DB from S3 (cold-start)."""
        if not object.__getattribute__(self, "_restored"):
            _download_from_s3(self.db_path)
            object.__setattr__(self, "_restored", True)

    def connect(self) -> sqlite3.Connection:
        self._ensure_restored()
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

    def save_to_s3(self) -> None:
        """Persist current DB to S3."""
        _upload_to_s3(self.db_path)

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            apply_migrations(conn)
