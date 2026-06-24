"""Phase 1 (AC1): signup/login/JWT/role enforcement."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import NotFoundError, PermissionDeniedError
from app.models import Role, User
from app.security import hash_password
from app.service.auth_service import AuthService


def _make_user(db: Session, email: str, password: str, role: Role = Role.USER) -> User:
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_signup_returns_201_and_user(client: TestClient) -> None:
    resp = client.post("/auth/signup", json={"email": "a@example.com", "password": "password123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert body["role"] == "USER"
    assert "password" not in body and "password_hash" not in body


def test_signup_duplicate_email_conflicts(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=payload).status_code == 201
    assert client.post("/auth/signup", json=payload).status_code == 409


def test_login_success_returns_jwt(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "b@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "c@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "c@example.com", "password": "wrongpass1"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401_generalized(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"email": "nope@example.com", "password": "password123"})
    assert resp.status_code == 401


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client: TestClient, db_session: Session) -> None:
    _make_user(db_session, "me@example.com", "password123")
    token = _login(client, "me@example.com", "password123")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_user_cannot_call_admin_endpoint_403(client: TestClient, db_session: Session) -> None:
    _make_user(db_session, "user@example.com", "password123", role=Role.USER)
    target = _make_user(db_session, "target@example.com", "password123")
    token = _login(client, "user@example.com", "password123")
    resp = client.post(
        f"/admin/users/{target.id}/promote", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_admin_can_promote_user(client: TestClient, db_session: Session) -> None:
    _make_user(db_session, "admin@example.com", "password123", role=Role.ADMIN)
    target = _make_user(db_session, "promote@example.com", "password123")
    token = _login(client, "admin@example.com", "password123")
    resp = client.post(
        f"/admin/users/{target.id}/promote", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"


def test_invalid_token_rejected(client: TestClient) -> None:
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_token_with_noninteger_sub_rejected(client: TestClient) -> None:
    # AUTH-002: a signed token whose sub is not an int must not raise an unhandled error.
    s = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "not-an-int",
            "role": "USER",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_login_unknown_user_runs_verification(client: TestClient) -> None:
    # SEC-004: unknown user still returns generalized 401 (verification path exercised).
    resp = client.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever12"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_promote_requires_admin_at_service_layer(db_session: Session) -> None:
    # AUTH-001: service rejects a non-admin actor even if the router gate were bypassed.
    actor = _make_user(db_session, "plainuser@example.com", "password123", role=Role.USER)
    target = _make_user(db_session, "victim@example.com", "password123")
    with pytest.raises(PermissionDeniedError):
        AuthService(db_session).promote_to_admin(actor=actor, target_user_id=target.id)


def test_promote_missing_target_404(db_session: Session) -> None:
    admin = _make_user(db_session, "root@example.com", "password123", role=Role.ADMIN)
    with pytest.raises(NotFoundError):
        AuthService(db_session).promote_to_admin(actor=admin, target_user_id=999999)
