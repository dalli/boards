"""Phase 3 (AC3 read, AC7, AC9): post & comment CRUD, ownership, optimistic lock, pagination."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.errors import PermissionDeniedError
from app.models import Board, BoardType, ContentStatus, Post, ReadVisibility, Role, User
from app.security import hash_password
from app.service.post_service import PostService


def _user(db: Session, email: str, role: Role = Role.USER) -> User:
    u = User(email=email, password_hash=hash_password("password123"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _token(client: TestClient, db: Session, email: str, role: Role = Role.USER) -> str:
    _user(db, email, role)
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]


def _board(
    db: Session,
    *,
    slug: str = "b",
    type: BoardType = BoardType.GENERAL,
    visibility: ReadVisibility = ReadVisibility.PUBLIC,
) -> Board:
    b = Board(name="B", slug=slug, type=type, read_visibility=visibility, description=None)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_post(client: TestClient, token: str, board_id: int, title: str = "t") -> dict:
    resp = client.post(
        f"/boards/{board_id}/posts",
        headers=_auth(token),
        json={"title": title, "content": "body"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- create / write gate (AC3 write reuse) ----


def test_user_creates_post_in_general(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g", type=BoardType.GENERAL)
    token = _token(client, db_session, "u@example.com")
    body = _create_post(client, token, board.id)
    assert body["status"] == "COMMITTED"
    assert body["version"] == 0


def test_anonymous_cannot_create_post_401(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    resp = client.post(f"/boards/{board.id}/posts", json={"title": "t", "content": "b"})
    assert resp.status_code == 401


def test_non_admin_cannot_post_to_notice_403(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="n", type=BoardType.NOTICE)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts", headers=_auth(token), json={"title": "t", "content": "b"}
    )
    assert resp.status_code == 403


def test_admin_can_post_to_notice_201(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="n", type=BoardType.NOTICE)
    token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    assert _create_post(client, token, board.id)["status"] == "COMMITTED"


# ---- read gate (AC3 read, E-04) ----


def test_public_post_readable_anonymous_200(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="pub", visibility=ReadVisibility.PUBLIC)
    token = _token(client, db_session, "u@example.com")
    post = _create_post(client, token, board.id)
    resp = client.get(f"/posts/{post['id']}")
    assert resp.status_code == 200


def test_authenticated_board_post_blocks_anonymous_401(
    client: TestClient, db_session: Session
) -> None:
    board = _board(db_session, slug="priv", visibility=ReadVisibility.AUTHENTICATED)
    token = _token(client, db_session, "u@example.com")
    post = _create_post(client, token, board.id)
    assert client.get(f"/posts/{post['id']}").status_code == 401
    assert client.get(f"/posts/{post['id']}", headers=_auth(token)).status_code == 200


def test_get_missing_post_404(client: TestClient) -> None:
    assert client.get("/posts/99999").status_code == 404


# ---- AC7: ownership edit/delete + optimistic lock ----


def test_author_can_update_own_post(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, token, board.id)
    resp = client.put(
        f"/posts/{post['id']}",
        headers=_auth(token),
        json={"title": "new", "content": "new body", "version": 0},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "new"
    assert resp.json()["version"] == 1


def test_other_user_cannot_update_post_403(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    other_token = _token(client, db_session, "other@example.com")
    resp = client.put(
        f"/posts/{post['id']}",
        headers=_auth(other_token),
        json={"title": "x", "content": "y", "version": 0},
    )
    assert resp.status_code == 403


def test_admin_can_update_others_post(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    admin_token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    resp = client.put(
        f"/posts/{post['id']}",
        headers=_auth(admin_token),
        json={"title": "modByAdmin", "content": "y", "version": 0},
    )
    assert resp.status_code == 200


def test_stale_version_conflicts_409(client: TestClient, db_session: Session) -> None:
    # E-05 optimistic lock: a second update with the old version must 409.
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, token, board.id)
    first = client.put(
        f"/posts/{post['id']}",
        headers=_auth(token),
        json={"title": "v1", "content": "c", "version": 0},
    )
    assert first.status_code == 200
    stale = client.put(
        f"/posts/{post['id']}",
        headers=_auth(token),
        json={"title": "v2", "content": "c", "version": 0},  # stale version
    )
    assert stale.status_code == 409


def test_author_can_delete_own_post(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, token, board.id)
    assert client.delete(f"/posts/{post['id']}", headers=_auth(token)).status_code == 204
    assert client.get(f"/posts/{post['id']}").status_code == 404


def test_other_user_cannot_delete_post_403(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    other_token = _token(client, db_session, "other@example.com")
    assert client.delete(f"/posts/{post['id']}", headers=_auth(other_token)).status_code == 403


# ---- Comments (AC7) ----


def test_create_and_list_comment(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "u@example.com")
    post = _create_post(client, token, board.id)
    resp = client.post(
        f"/posts/{post['id']}/comments", headers=_auth(token), json={"content": "hi"}
    )
    assert resp.status_code == 201
    listing = client.get(f"/posts/{post['id']}/comments")
    assert listing.status_code == 200
    assert [c["content"] for c in listing.json()] == ["hi"]


def test_other_user_cannot_delete_comment_403(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    cid = client.post(
        f"/posts/{post['id']}/comments", headers=_auth(owner_token), json={"content": "c"}
    ).json()["id"]
    other_token = _token(client, db_session, "other@example.com")
    assert client.delete(f"/comments/{cid}", headers=_auth(other_token)).status_code == 403


def test_author_can_delete_comment(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "u@example.com")
    post = _create_post(client, token, board.id)
    cid = client.post(
        f"/posts/{post['id']}/comments", headers=_auth(token), json={"content": "c"}
    ).json()["id"]
    assert client.delete(f"/comments/{cid}", headers=_auth(token)).status_code == 204


def test_comment_on_authenticated_board_blocks_anonymous(
    client: TestClient, db_session: Session
) -> None:
    board = _board(db_session, slug="priv", visibility=ReadVisibility.AUTHENTICATED)
    token = _token(client, db_session, "u@example.com")
    post = _create_post(client, token, board.id)
    assert client.get(f"/posts/{post['id']}/comments").status_code == 401


# ---- F-003: comment edit (AC7 댓글 PUT) ----


def _make_comment(client: TestClient, token: str, post_id: int, content: str = "c") -> int:
    return client.post(
        f"/posts/{post_id}/comments", headers=_auth(token), json={"content": content}
    ).json()["id"]


def test_author_can_edit_own_comment(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, token, board.id)
    cid = _make_comment(client, token, post["id"])
    resp = client.put(
        f"/comments/{cid}", headers=_auth(token), json={"content": "edited"}
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "edited"


def test_other_user_cannot_edit_comment_403(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    cid = _make_comment(client, owner_token, post["id"])
    other_token = _token(client, db_session, "other@example.com")
    resp = client.put(f"/comments/{cid}", headers=_auth(other_token), json={"content": "x"})
    assert resp.status_code == 403


def test_admin_can_edit_others_comment(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    owner_token = _token(client, db_session, "owner@example.com")
    post = _create_post(client, owner_token, board.id)
    cid = _make_comment(client, owner_token, post["id"])
    admin_token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    resp = client.put(
        f"/comments/{cid}", headers=_auth(admin_token), json={"content": "modbyadmin"}
    )
    assert resp.status_code == 200


# ---- F-002: NOTICE write gate re-applied on post update ----


def test_admin_authored_notice_post_update_requires_admin(
    client: TestClient, db_session: Session
) -> None:
    # An ADMIN creates a NOTICE post, then is demoted conceptually: a non-admin cannot update it
    # even if they were the author (write gate is re-checked). Here we assert the admin can update.
    board = _board(db_session, slug="n", type=BoardType.NOTICE)
    admin_token = _token(client, db_session, "admin@example.com", Role.ADMIN)
    post = _create_post(client, admin_token, board.id)
    resp = client.put(
        f"/posts/{post['id']}",
        headers=_auth(admin_token),
        json={"title": "upd", "content": "c", "version": 0},
    )
    assert resp.status_code == 200


def _seed_notice_post_by_user(db_session: Session) -> tuple[int, User]:
    """Directly seed a NOTICE post authored by a non-admin (unreachable via API write gate),
    so the update/delete write-gate re-checks (F-002 / NV-002) can be genuinely exercised."""
    board = _board(db_session, slug="n", type=BoardType.NOTICE)
    user = _user(db_session, "naughty@example.com", Role.USER)
    post = Post(
        board_id=board.id,
        author_id=user.id,
        title="t",
        content="c",
        status=ContentStatus.COMMITTED,
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post.id, user


def test_non_admin_author_cannot_update_notice_post(db_session: Session) -> None:
    # NV-001/F-002: even the recorded author (non-admin) is blocked by the NOTICE write gate.

    post_id, user = _seed_notice_post_by_user(db_session)

    with pytest.raises(PermissionDeniedError):
        PostService(db_session).update_post(
            post_id=post_id, actor=user, title="x", content="y", client_version=0
        )


def test_non_admin_author_cannot_delete_notice_post(db_session: Session) -> None:
    # NV-002: delete must also re-apply the NOTICE write gate.

    post_id, user = _seed_notice_post_by_user(db_session)

    with pytest.raises(PermissionDeniedError):
        PostService(db_session).delete_post(post_id=post_id, actor=user)
