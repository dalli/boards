"""Shared test fixtures.

Unit tests run against an in-memory SQLite DB for speed. Postgres-specific constructs
(partial unique indexes via postgresql_where, enum types) degrade gracefully on SQLite;
DB-level constraint behavior that is Postgres-only is exercised by integration tests.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.security as security_module
from app.db import Base, get_db
from app.main import create_app
from app.storage import InMemoryStorageClient, get_storage


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the real bcrypt code paths but at minimum cost so the suite stays fast.

    The production cost floor (>=12, security.md S-02) is enforced by config validation and
    verified separately in test_config; here we only speed up hashing in tests.
    """
    import bcrypt

    original_gensalt = bcrypt.gensalt
    monkeypatch.setattr(
        security_module.bcrypt,
        "gensalt",
        lambda rounds=4: original_gensalt(4),
    )
    # Recompute the module-level dummy hash under the fast salt.
    monkeypatch.setattr(
        security_module,
        "DUMMY_PASSWORD_HASH",
        bcrypt.hashpw(security_module._prepare("dummy-password"), original_gensalt(4)).decode(
            "ascii"
        ),
    )


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def storage() -> InMemoryStorageClient:
    return InMemoryStorageClient()


@pytest.fixture
def client(db_session: Session, storage: InMemoryStorageClient) -> Iterator[TestClient]:
    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
