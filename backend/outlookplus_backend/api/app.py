from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from outlookplus_backend.api.routes import router
from outlookplus_backend.wiring import get_db, init_storage


class _UserEmailMiddleware(BaseHTTPMiddleware):
    """Route each request to the correct per-email database.

    The frontend sends the IMAP username as the ``X-User-Email`` header.
    This middleware tells the DbManager which email's DB to use before
    the route handler runs.
    """

    async def dispatch(self, request: Request, call_next):
        email = request.headers.get("X-User-Email")
        get_db().set_active_email(email.strip() if email else None)
        return await call_next(request)


class _S3SyncMiddleware(BaseHTTPMiddleware):
    """After any mutating request (POST/PATCH/PUT/DELETE), persist the
    SQLite database to S3 so the next Lambda cold-start can restore it."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            try:
                get_db().save_to_s3()
            except Exception:
                pass  # best-effort; don't break the response
        return response


def create_app() -> FastAPI:
    init_storage()
    app = FastAPI(title="OutlookPlus Backend", version="1.0.0")

    # Dev/demo CORS: permissive by explicit user choice.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Order matters: _UserEmailMiddleware runs BEFORE _S3SyncMiddleware,
    # so the active email is set before any DB operation / S3 upload.
    app.add_middleware(_S3SyncMiddleware)
    app.add_middleware(_UserEmailMiddleware)

    app.include_router(router)
    return app
