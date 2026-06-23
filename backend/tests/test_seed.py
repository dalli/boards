"""Y-02: initial admin seed is idempotent and refuses empty passwords."""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

import app.seed as seed_module
from app.config import Settings
from app.models import Role, User
from app.repository.user_repository import UserRepository
from app.security import hash_password


@pytest.fixture
def patched_seed(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> Iterator[None]:
    # seed_admin() closes its session in finally; keep the shared test session open
    # by making close() a no-op (the db_session fixture owns the real teardown).
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    yield


def _settings(password: str | None) -> Settings:
    return Settings(seed_admin_email="admin@example.com", seed_admin_password=password)


def test_seed_refuses_empty_password(
    monkeypatch: pytest.MonkeyPatch, patched_seed: None
) -> None:
    monkeypatch.setattr(seed_module, "get_settings", lambda: _settings(None))
    assert seed_module.seed_admin() == 1


def test_seed_creates_admin(
    monkeypatch: pytest.MonkeyPatch, patched_seed: None, db_session: Session
) -> None:
    monkeypatch.setattr(seed_module, "get_settings", lambda: _settings("strongpass1"))
    assert seed_module.seed_admin() == 0
    user = UserRepository(db_session).get_active_by_email("admin@example.com")
    assert user is not None and user.role is Role.ADMIN


def test_seed_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, patched_seed: None, db_session: Session
) -> None:
    monkeypatch.setattr(seed_module, "get_settings", lambda: _settings("strongpass1"))
    assert seed_module.seed_admin() == 0
    assert seed_module.seed_admin() == 0
    admins = [u for u in db_session.query(User).all() if u.role is Role.ADMIN]
    assert len(admins) == 1


def test_seed_promotes_existing_user(
    monkeypatch: pytest.MonkeyPatch, patched_seed: None, db_session: Session
) -> None:
    existing = User(
        email="admin@example.com", password_hash=hash_password("x12345678"), role=Role.USER
    )
    db_session.add(existing)
    db_session.commit()
    monkeypatch.setattr(seed_module, "get_settings", lambda: _settings("strongpass1"))
    assert seed_module.seed_admin() == 0
    db_session.refresh(existing)
    assert existing.role is Role.ADMIN
