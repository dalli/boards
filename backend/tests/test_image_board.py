"""Phase 5 (AC5, AC6): image board — multi-image enforcement (E-01) + thumbnails."""
from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Attachment, Board, BoardType, ReadVisibility, Role, User
from app.security import hash_password
from app.storage import InMemoryStorageClient


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


def _image_board(db: Session, slug: str = "img") -> Board:
    b = Board(
        name="Gallery",
        slug=slug,
        type=BoardType.IMAGE,
        read_visibility=ReadVisibility.PUBLIC,
        description=None,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _png(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


def _create_image_post(client: TestClient, token: str, board_id: int, n_images: int):
    files = [("files", (f"p{i}.png", _png((i, i, i)), "image/png")) for i in range(n_images)]
    return client.post(
        f"/boards/{board_id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "gallery post", "content": "body"},
        files=files,
    )


# ---- AC5: image-required invariant (E-01) ----


def test_image_board_requires_at_least_one_image_422(
    client: TestClient, db_session: Session
) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    # no files at all
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[],
    )
    assert resp.status_code == 422


def test_image_board_json_create_route_rejected_422(
    client: TestClient, db_session: Session
) -> None:
    # R-01/R-06: the no-attachment JSON create route must refuse IMAGE boards (E-01).
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts",
        headers=_auth(token),
        json={"title": "t", "content": "c"},
    )
    assert resp.status_code == 422


def test_image_board_rejects_non_image_422(client: TestClient, db_session: Session) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("notes.txt", b"not an image", "text/plain"))],
    )
    assert resp.status_code == 422


def test_image_post_each_attachment_has_thumbnail_key(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    resp = _create_image_post(client, token, board.id, n_images=3)
    assert resp.status_code == 201, resp.text
    post_id = resp.json()["id"]
    atts = client.get(f"/posts/{post_id}/attachments").json()
    assert len(atts) == 3
    assert all(a["is_image"] for a in atts)
    assert all(a["thumbnail_url"] is not None for a in atts)
    # 3 originals + 3 thumbnails stored
    assert len(storage.objects) == 6
    # R-08: assert the persisted thumbnail_key column is set (AC5 explicit criterion).
    rows = db_session.query(Attachment).filter(Attachment.post_id == post_id).all()
    assert len(rows) == 3
    assert all(r.thumbnail_key is not None for r in rows)


def test_deleting_last_image_rejected_422(
    client: TestClient, db_session: Session
) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    post_id = _create_image_post(client, token, board.id, n_images=1).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    resp = client.delete(f"/posts/{post_id}/attachments/{att_id}", headers=_auth(token))
    assert resp.status_code == 422


def test_deleting_non_last_image_allowed(
    client: TestClient, db_session: Session
) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    post_id = _create_image_post(client, token, board.id, n_images=2).json()["id"]
    atts = client.get(f"/posts/{post_id}/attachments").json()
    resp = client.delete(
        f"/posts/{post_id}/attachments/{atts[0]['id']}", headers=_auth(token)
    )
    assert resp.status_code == 204
    remaining = client.get(f"/posts/{post_id}/attachments").json()
    assert len(remaining) == 1


# ---- AC6: thumbnail grid + lightbox original ----


def test_image_post_returns_thumbnail_url_array_for_grid(
    client: TestClient, db_session: Session
) -> None:
    # R-07/AC6: GET /posts/{id} itself returns the attachment thumbnail array for the grid.
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    post_id = _create_image_post(client, token, board.id, n_images=2).json()["id"]
    detail = client.get(f"/posts/{post_id}").json()
    assert "attachments" in detail
    thumbnail_urls = [a["thumbnail_url"] for a in detail["attachments"]]
    assert len(thumbnail_urls) == 2
    assert all(u and "/thumbnails/" in u for u in thumbnail_urls)


def test_original_url_for_lightbox(client: TestClient, db_session: Session) -> None:
    board = _image_board(db_session)
    token = _token(client, db_session, "u@example.com")
    post_id = _create_image_post(client, token, board.id, n_images=1).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    resp = client.get(f"/attachments/{att_id}/original-url")
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert "/attachments/" in url and "expires_in=" in url
