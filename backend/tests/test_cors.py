"""CORS preflight is answered for the configured SPA origin (browser cross-origin support)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_preflight_allows_configured_origin(client: TestClient) -> None:
    resp = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_actual_request_carries_cors_header(client: TestClient) -> None:
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
