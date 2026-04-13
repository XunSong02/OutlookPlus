from __future__ import annotations

from functools import lru_cache

from outlookplus_backend.config import load_reply_need_config, load_storage_config
from outlookplus_backend.credentials import CredentialStore
from outlookplus_backend.ics import IcsExtractor
from outlookplus_backend.llm import GeminiClient, PromptBuilder, RateLimiter, RetryPolicy, StrictJsonValidator
from outlookplus_backend.email_actions import EmailActionService
from outlookplus_backend.email_analysis import EmailAnalysisClassifier, EmailAnalysisService
from outlookplus_backend.meeting import MeetingClassifier, MeetingService
from outlookplus_backend.persistence.db import Db, DbManager
from outlookplus_backend.ai_assistant import AiAssistantService
from outlookplus_backend.reply_need import ReplyNeedService
from outlookplus_backend.smtp import SmtpClient


@lru_cache(maxsize=1)
def get_db() -> DbManager:
    """Return the global DbManager (per-email routing)."""
    cfg = load_storage_config()
    import os
    base_dir = os.path.dirname(cfg.db_path) or "data"
    return DbManager(base_dir=base_dir)


def init_storage() -> None:
    db = get_db()
    db.init_schema()
    # Ensure the credentials table exists on startup.
    get_credential_store()


@lru_cache(maxsize=1)
def get_credential_store() -> CredentialStore:
    return CredentialStore(db=get_db())


@lru_cache(maxsize=1)
def _prompt_builder() -> PromptBuilder:
    return PromptBuilder()


@lru_cache(maxsize=1)
def _validator() -> StrictJsonValidator:
    return StrictJsonValidator()


@lru_cache(maxsize=1)
def _gemini() -> GeminiClient:
    # Conservative defaults: no enforced rate limit; retries enabled.
    # gemini_credentials=None → env-var fallback (default for local dev).
    # Routes will inject per-user credentials when available.
    return GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())


def get_gemini_for_user(user_id: str) -> GeminiClient:
    """Return a GeminiClient wired with the user's stored credentials (if any)."""
    creds = get_credential_store().get_gemini(user_id=user_id)
    if creds is not None:
        return GeminiClient(
            rate_limiter=RateLimiter(min_interval_seconds=0.0),
            retry_policy=RetryPolicy(),
            gemini_credentials=creds,
        )
    return _gemini()


@lru_cache(maxsize=1)
def get_smtp_client() -> SmtpClient:
    # Conservative defaults: no enforced rate limit; retries enabled.
    return SmtpClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())


def get_smtp_for_user(user_id: str) -> SmtpClient:
    """Return an SmtpClient wired with the user's stored credentials (if any)."""
    creds = get_credential_store().get_smtp(user_id=user_id)
    if creds is not None:
        return SmtpClient(
            rate_limiter=RateLimiter(min_interval_seconds=0.0),
            retry_policy=RetryPolicy(),
            smtp_credentials=creds,
        )
    return get_smtp_client()


@lru_cache(maxsize=1)
def _ics() -> IcsExtractor:
    return IcsExtractor()


@lru_cache(maxsize=1)
def get_meeting_service() -> MeetingService:
    return MeetingService(db=get_db())


@lru_cache(maxsize=1)
def get_meeting_classifier() -> MeetingClassifier:
    return MeetingClassifier(
        db=get_db(),
        prompt_builder=_prompt_builder(),
        gemini=_gemini(),
        validator=_validator(),
        ics_extractor=_ics(),
    )


@lru_cache(maxsize=1)
def get_reply_need_service() -> ReplyNeedService:
    return ReplyNeedService(
        db=get_db(),
        meeting_service=get_meeting_service(),
        prompt_builder=_prompt_builder(),
        gemini=_gemini(),
        validator=_validator(),
        config=load_reply_need_config(),
    )


@lru_cache(maxsize=1)
def get_email_analysis_service() -> EmailAnalysisService:
    return EmailAnalysisService(db=get_db())


@lru_cache(maxsize=1)
def get_email_analysis_classifier() -> EmailAnalysisClassifier:
    return EmailAnalysisClassifier(
        db=get_db(),
        prompt_builder=_prompt_builder(),
        gemini=_gemini(),
        validator=_validator(),
    )


@lru_cache(maxsize=1)
def get_ai_assistant_service() -> AiAssistantService:
    return AiAssistantService(
        db=get_db(),
        prompt_builder=_prompt_builder(),
        gemini=_gemini(),
        validator=_validator(),
    )


@lru_cache(maxsize=1)
def get_email_action_service() -> EmailActionService:
    return EmailActionService(db=get_db())


def build_worker():
    from outlookplus_backend.worker.ingestion_worker import IngestionWorker
    from outlookplus_backend.imap.client import MailboxClient

    init_storage()
    return IngestionWorker(
        db=get_db(),
        mailbox=MailboxClient(),
        meeting_classifier=get_meeting_classifier(),
        email_analysis_classifier=get_email_analysis_classifier(),
    )


def build_worker_for_user(user_id: str):
    """Build an ingestion worker wired with the user's stored IMAP credentials."""
    from outlookplus_backend.worker.ingestion_worker import IngestionWorker
    from outlookplus_backend.imap.client import MailboxClient

    init_storage()
    imap_creds = get_credential_store().get_imap(user_id=user_id)
    return IngestionWorker(
        db=get_db(),
        mailbox=MailboxClient(imap_credentials=imap_creds),
        meeting_classifier=get_meeting_classifier(),
        email_analysis_classifier=get_email_analysis_classifier(),
    )
