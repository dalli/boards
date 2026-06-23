"""FastAPI application entry point.

Registers routers and a global handler that maps domain AppError → HTTP response,
keeping HTTP concerns at the edge (§5 layering).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import AppError


def create_app() -> FastAPI:
    app = FastAPI(title="Boards API", version="0.1.0")

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
    from app.api import auth as auth_api
    from app.api import boards as boards_api
    from app.api import posts as posts_api

    app.include_router(auth_api.router)
    app.include_router(boards_api.router)
    app.include_router(posts_api.router)


app = create_app()
