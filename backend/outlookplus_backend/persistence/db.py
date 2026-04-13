from __future__ import annotations

import os
import re
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


def _download_from_s3(db_path: str, s3_key: str) -> None:
    """Download DB from S3 to local path if it exists."""
    bucket = _s3_bucket()
    if not bucket:
        return
    Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)
    try:
        _get_s3().download_file(bucket, s3_key, db_path)
    except _get_s3().exceptions.ClientError:
        pass  # First run – no DB in S3 yet, that's fine.


def _upload_to_s3(db_path: str, s3_key: str) -> None:
    """Checkpoint WAL then upload local DB to S3."""
    bucket = _s3_bucket()
    if not bucket:
        return
    if os.path.exists(db_path):
        # Force WAL data into the main database file before uploading.
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
        except Exception:
            pass
        _get_s3().upload_file(db_path, bucket, s3_key)


def _sanitize_email(email: str) -> str:
    """Make an email address safe for use as a directory / S3 key component."""
    return re.sub(r"[^a-zA-Z0-9@._-]", "_", email.lower().strip())


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
    s3_key: str = "outlookplus.db"
    _restored: bool = False

    def _ensure_restored(self) -> None:
        """On first access, pull the DB from S3 (cold-start)."""
        if not object.__getattribute__(self, "_restored"):
            _download_from_s3(self.db_path, self.s3_key)
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
        _upload_to_s3(self.db_path, self.s3_key)

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            apply_migrations(conn)


class DbManager:
    """Proxy that dispatches to per-email Db instances.

    Exposes the same interface as ``Db`` (connect / save_to_s3 / init_schema /
    db_path) so all existing code that depends on ``Db`` works unchanged.
    The *active_email* is set per-request by a middleware.
    """

    def __init__(self, base_dir: str, default_db_path: str | None = None) -> None:
        self._base_dir = base_dir
        self._default_db_path = default_db_path or os.path.join(base_dir, "outlookplus.db")
        self._dbs: dict[str, Db] = {}
        self._active_email: str | None = None

    # -- email routing -------------------------------------------------------

    @property
    def active_email(self) -> str | None:
        return self._active_email

    def set_active_email(self, email: str | None) -> None:
        self._active_email = email
        db = self._get_active_db()
        # On warm Lambda instances the local DB may be stale (another
        # instance handled the ingest and uploaded to S3).  Reset the
        # flag so the next connect() re-downloads from S3.
        if _s3_bucket():
            object.__setattr__(db, "_restored", False)

    def _get_active_db(self) -> Db:
        key = self._active_email or "__default__"
        if key not in self._dbs:
            if self._active_email:
                safe = _sanitize_email(self._active_email)
                db_path = os.path.join(self._base_dir, safe, "outlookplus.db")
                s3_key = f"users/{safe}/outlookplus.db"
            else:
                db_path = self._default_db_path
                s3_key = "outlookplus.db"
            db = Db(db_path=db_path, s3_key=s3_key)
            db.init_schema()
            self._dbs[key] = db
        return self._dbs[key]

    # -- Db-compatible interface ---------------------------------------------

    def connect(self) -> sqlite3.Connection:
        return self._get_active_db().connect()

    def save_to_s3(self) -> None:
        self._get_active_db().save_to_s3()

    def init_schema(self) -> None:
        self._get_active_db().init_schema()

    @property
    def db_path(self) -> str:
        return self._get_active_db().db_path
