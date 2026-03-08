from __future__ import annotations

from functools import lru_cache

from outlookplus_backend.config import load_reply_need_config, load_storage_config
from outlookplus_backend.ics import IcsExtractor
from outlookplus_backend.llm import GeminiClient, PromptBuilder, RateLimiter, RetryPolicy, StrictJsonValidator
from outlookplus_backend.email_actions import EmailActionService
from outlookplus_backend.email_analysis import EmailAnalysisClassifier, EmailAnalysisService
from outlookplus_backend.meeting import MeetingClassifier, MeetingService
from outlookplus_backend.persistence.db import Db
from outlookplus_backend.ai_assistant import AiAssistantService
from outlookplus_backend.reply_need import ReplyNeedService
from outlookplus_backend.smtp import SmtpClient


@lru_cache(maxsize=1)
def get_db() -> Db:
    cfg = load_storage_config()
    db = Db(db_path=cfg.db_path)
    return db


def init_storage() -> None:
    db = get_db()
    db.init_schema()


@lru_cache(maxsize=1)
def _prompt_builder() -> PromptBuilder:
    return PromptBuilder()


@lru_cache(maxsize=1)
def _validator() -> StrictJsonValidator:
    return StrictJsonValidator()


@lru_cache(maxsize=1)
def _gemini() -> GeminiClient:
    # Conservative defaults: no enforced rate limit; retries enabled.
    return GeminiClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())


@lru_cache(maxsize=1)
def get_smtp_client() -> SmtpClient:
    # Conservative defaults: no enforced rate limit; retries enabled.
    return SmtpClient(rate_limiter=RateLimiter(min_interval_seconds=0.0), retry_policy=RetryPolicy())


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
