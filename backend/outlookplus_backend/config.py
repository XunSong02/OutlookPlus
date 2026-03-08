from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class StorageConfig:
    db_path: str
    attachments_dir: str


@dataclass(frozen=True)
class AuthConfig:
    # Auth mode:
    # - A: demo / no auth (all requests treated as single demo user)
    # - B: dev stub (Authorization: Bearer dev:<userId>)
    # - C: production (not implemented here)
    mode: str
    # Dev-only stub verifier:
    # - Accepts Authorization: Bearer dev:<userId>
    # - Or matches OUTLOOKPLUS_DEV_TOKEN exactly and returns OUTLOOKPLUS_DEV_USER_ID
    dev_token: str | None
    dev_user_id: str | None


@dataclass(frozen=True)
class ReplyNeedConfig:
    min_confidence: float


def load_storage_config() -> StorageConfig:
    return StorageConfig(
        db_path=os.getenv("OUTLOOKPLUS_DB_PATH", "data/outlookplus.db"),
        attachments_dir=os.getenv("OUTLOOKPLUS_ATTACHMENTS_DIR", "data/attachments"),
    )


def load_auth_config() -> AuthConfig:
    return AuthConfig(
        mode=os.getenv("OUTLOOKPLUS_AUTH_MODE", "A"),
        dev_token=os.getenv("OUTLOOKPLUS_DEV_TOKEN"),
        dev_user_id=os.getenv("OUTLOOKPLUS_DEV_USER_ID"),
    )


def load_reply_need_config() -> ReplyNeedConfig:
    return ReplyNeedConfig(
        min_confidence=float(os.getenv("REPLY_NEED_MIN_CONFIDENCE", "0.65"))
    )
