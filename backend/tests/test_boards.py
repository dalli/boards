"""Phase 2 (AC2, AC3 write/read-visibility): board CRUD + permission model."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.errors import PermissionDeniedError
from app.models import Board, BoardType, ReadVisibility, Role, User
from app.security import hash_password
from app.service.board_service import BoardService
from app.service.permissions import ensure_can_write_board


def _make_user(db: Session, email: str, role: Role = Role.USER) -> User:
    user = User(email=email, password_hash=hash_password("password123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _token(client: TestClient, db: Session, email: str, role: Role) -> str:
    _make_user(db, email, role)
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]


def _make_board(
    db: Session,
    *,
    slug: str = "b1",
    type: BoardType = BoardType.GENERAL,
    visibility: ReadVisibility = ReadVisibility.PUBLIC,
) -> Board:
    board = Board(name="Board", slug=slug, type=type, read_visibility=visibility, description=None)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


# ---- AC2: board creation ----


def test_admin_creates_board_201(client: TestClient, db_session: Session) -> None:
    token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    resp = client.post(
        "/admin/boards",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "공지",
            "slug": "notice",
            "type": "NOTICE",
            "read_visibility": "PUBLIC",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "NOTICE"
    assert body["read_visibility"] == "PUBLIC"
    assert body["slug"] == "notice"


def test_non_admin_cannot_create_board_403(client: TestClient, db_session: Session) -> None:
    token = _token(client, db_session, "user@example.com", Role.USER)
    resp = client.post(
        "/admin/boards",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "x", "slug": "x", "type": "GENERAL", "read_visibility": "PUBLIC"},
    )
    assert resp.status_code == 403


def test_create_board_requires_auth_401(client: TestClient) -> None:
    resp = client.post(
        "/admin/boards",
        json={"name": "x", "slug": "x", "type": "GENERAL", "read_visibility": "PUBLIC"},
    )
    assert resp.status_code == 401


def test_create_board_rejects_invalid_type_422(client: TestClient, db_session: Session) -> None:
    token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    resp = client.post(
        "/admin/boards",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "x", "slug": "x", "type": "BOGUS", "read_visibility": "PUBLIC"},
    )
    assert resp.status_code == 422


def test_duplicate_slug_conflicts_409(client: TestClient, db_session: Session) -> None:
    token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    payload = {"name": "x", "slug": "dup", "type": "GENERAL", "read_visibility": "PUBLIC"}
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/admin/boards", headers=headers, json=payload).status_code == 201
    assert client.post("/admin/boards", headers=headers, json=payload).status_code == 409


# ---- AC3 (read_visibility, E-04) ----


def test_public_board_readable_unauthenticated_200(client: TestClient, db_session: Session) -> None:
    board = _make_board(db_session, slug="pub", visibility=ReadVisibility.PUBLIC)
    resp = client.get(f"/boards/{board.id}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "pub"


def test_authenticated_board_blocks_anonymous_401(
    client: TestClient, db_session: Session
) -> None:
    board = _make_board(db_session, slug="priv", visibility=ReadVisibility.AUTHENTICATED)
    resp = client.get(f"/boards/{board.id}")
    assert resp.status_code == 401


def test_authenticated_board_readable_with_token_200(
    client: TestClient, db_session: Session
) -> None:
    board = _make_board(db_session, slug="priv2", visibility=ReadVisibility.AUTHENTICATED)
    token = _token(client, db_session, "u@example.com", Role.USER)
    resp = client.get(f"/boards/{board.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_get_missing_board_404(client: TestClient) -> None:
    assert client.get("/boards/99999").status_code == 404


def test_list_boards_anonymous_sees_only_public(client: TestClient, db_session: Session) -> None:
    # FINDING-001: anonymous listing must NOT leak AUTHENTICATED board metadata.
    _make_board(db_session, slug="l1", visibility=ReadVisibility.PUBLIC)
    _make_board(db_session, slug="l2", visibility=ReadVisibility.AUTHENTICATED)
    resp = client.get("/boards")
    assert resp.status_code == 200
    assert {b["slug"] for b in resp.json()} == {"l1"}


def test_list_boards_authenticated_sees_all(client: TestClient, db_session: Session) -> None:
    _make_board(db_session, slug="l1", visibility=ReadVisibility.PUBLIC)
    _make_board(db_session, slug="l2", visibility=ReadVisibility.AUTHENTICATED)
    token = _token(client, db_session, "viewer@example.com", Role.USER)
    resp = client.get("/boards", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert {b["slug"] for b in resp.json()} == {"l1", "l2"}


def test_list_boards_invalid_token_treated_as_anonymous(
    client: TestClient, db_session: Session
) -> None:
    # FINDING-008: an invalid bearer token must not widen visibility beyond anonymous.
    _make_board(db_session, slug="l1", visibility=ReadVisibility.PUBLIC)
    _make_board(db_session, slug="l2", visibility=ReadVisibility.AUTHENTICATED)
    resp = client.get("/boards", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 200
    assert {b["slug"] for b in resp.json()} == {"l1"}


# ---- delete ----


def test_admin_deletes_board_204(client: TestClient, db_session: Session) -> None:
    board = _make_board(db_session, slug="del")
    token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    resp = client.delete(
        f"/admin/boards/{board.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204
    assert client.get(f"/boards/{board.id}").status_code == 404


def test_non_admin_cannot_delete_board_403(client: TestClient, db_session: Session) -> None:
    board = _make_board(db_session, slug="del2")
    token = _token(client, db_session, "user@example.com", Role.USER)
    resp = client.delete(
        f"/admin/boards/{board.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


# ---- service-layer write gate (AC3 write side; reused in Phase 3) ----


def test_notice_write_gate_blocks_non_admin(db_session: Session) -> None:
    board = _make_board(db_session, slug="n", type=BoardType.NOTICE)
    user = _make_user(db_session, "writer@example.com", Role.USER)
    with pytest.raises(PermissionDeniedError):
        ensure_can_write_board(board, user)


def test_notice_write_gate_allows_admin(db_session: Session) -> None:
    board = _make_board(db_session, slug="n2", type=BoardType.NOTICE)
    admin = _make_user(db_session, "adm@example.com", Role.ADMIN)
    ensure_can_write_board(board, admin)  # no raise


def test_general_write_gate_allows_user(db_session: Session) -> None:
    board = _make_board(db_session, slug="g", type=BoardType.GENERAL)
    user = _make_user(db_session, "gu@example.com", Role.USER)
    ensure_can_write_board(board, user)  # no raise


def test_create_board_service_rejects_non_admin(db_session: Session) -> None:
    user = _make_user(db_session, "nope@example.com", Role.USER)
    with pytest.raises(PermissionDeniedError):
        BoardService(db_session).create_board(
            actor=user,
            name="x",
            slug="x",
            type=BoardType.GENERAL,
            read_visibility=ReadVisibility.PUBLIC,
            description=None,
        )
