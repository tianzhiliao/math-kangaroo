from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.content import router as content_router
from .routers.explanation import router as explanation_router
from .routers.tts import router as tts_router


def create_app() -> FastAPI:
    app = FastAPI(title="Math prep API", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(content_router)
    app.include_router(tts_router)
    app.include_router(explanation_router)
    return app


app = create_app()
