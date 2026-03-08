from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from outlookplus_backend.api.routes import router
from outlookplus_backend.wiring import init_storage


def create_app() -> FastAPI:
    init_storage()
    app = FastAPI(title="OutlookPlus Backend")

    # Dev/demo CORS: permissive by explicit user choice.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app
