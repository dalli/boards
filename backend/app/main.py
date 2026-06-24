"""FastAPI application entry point.

Registers routers and a global handler that maps domain AppError → HTTP response,
keeping HTTP concerns at the edge (§5 layering).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError


def create_app() -> FastAPI:
    app = FastAPI(title="Boards API", version="0.1.0")

    # CORS: the SPA is a separate browser origin (e.g. :5173) calling the API (:8000), so the
    # browser issues a preflight that must be answered. Origins are allowlisted via settings.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    """Routers are added per phase as their modules land."""
    from app.api import attachments as attachments_api
    from app.api import auth as auth_api
    from app.api import boards as boards_api
    from app.api import posts as posts_api

    app.include_router(auth_api.router)
    app.include_router(boards_api.router)
    app.include_router(posts_api.router)
    app.include_router(attachments_api.router)


app = create_app()
