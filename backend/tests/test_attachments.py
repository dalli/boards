"""Phase 4 (AC4): backend-mediated upload, presigned download, validation, S3-first delete."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ValidationFailedError
from app.models import Attachment, Board, BoardType, ContentStatus, ReadVisibility, Role, User
from app.security import hash_password
from app.service.file_validation import sniff_image_type, validate_upload
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


def _board(
    db: Session,
    *,
    slug: str = "g",
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


def _png_bytes() -> bytes:
    """A minimal valid 1x1 PNG produced by Pillow."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


# ---- validation unit tests (S-03) ----


def test_sniff_detects_png() -> None:
    assert sniff_image_type(_png_bytes()) == "image/png"


def test_sniff_rejects_non_image() -> None:
    assert sniff_image_type(b"just text, not an image") is None


def test_validate_image_board_rejects_non_image() -> None:
    with pytest.raises(ValidationFailedError):
        validate_upload(data=b"plain text", declared_content_type="text/plain", require_image=True)


def test_validate_general_accepts_text() -> None:
    is_image, ct = validate_upload(
        data=b"hello world", declared_content_type="text/plain", require_image=False
    )
    assert is_image is False
    assert ct == "text/plain"


def test_validate_rejects_empty() -> None:
    with pytest.raises(ValidationFailedError):
        validate_upload(data=b"", declared_content_type="text/plain", require_image=False)


# ---- upload (AC4) ----


def test_upload_general_file_creates_committed_post(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _board(db_session, slug="g", type=BoardType.GENERAL)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("note.txt", b"hello attachment", "text/plain"))],
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "COMMITTED"
    # object actually stored in (fake) S3
    assert len(storage.objects) == 1


def test_upload_image_generates_thumbnail(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _board(db_session, slug="g", type=BoardType.GENERAL)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("pic.png", _png_bytes(), "image/png"))],
    )
    assert resp.status_code == 201
    post_id = resp.json()["id"]
    atts = client.get(f"/posts/{post_id}/attachments").json()
    assert len(atts) == 1
    assert atts[0]["is_image"] is True
    assert atts[0]["thumbnail_url"] is not None
    # original + thumbnail both stored
    assert len(storage.objects) == 2


def test_upload_requires_auth_401(client: TestClient, db_session: Session) -> None:
    board = _board(db_session, slug="g")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"x", "text/plain"))],
    )
    assert resp.status_code == 401


def test_notice_board_upload_blocks_non_admin_403(
    client: TestClient, db_session: Session
) -> None:
    board = _board(db_session, slug="n", type=BoardType.NOTICE)
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"x", "text/plain"))],
    )
    assert resp.status_code == 403


# ---- download (AC4 presigned, read_visibility gate) ----


def test_original_url_returned_for_public(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _board(db_session, slug="pub", visibility=ReadVisibility.PUBLIC)
    token = _token(client, db_session, "u@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    resp = client.get(f"/attachments/{att_id}/original-url")
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("https://storage.local/")


def test_original_url_blocked_for_anonymous_on_authenticated_board(
    client: TestClient, db_session: Session
) -> None:
    board = _board(db_session, slug="priv", visibility=ReadVisibility.AUTHENTICATED)
    token = _token(client, db_session, "u@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    att_id = client.get(
        f"/posts/{post_id}/attachments", headers=_auth(token)
    ).json()[0]["id"]
    assert client.get(f"/attachments/{att_id}/original-url").status_code == 401
    assert (
        client.get(f"/attachments/{att_id}/original-url", headers=_auth(token)).status_code == 200
    )


# ---- delete (NV2-002 S3-first) ----


def test_delete_attachment_removes_s3_then_row(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    assert len(storage.objects) == 1
    resp = client.delete(
        f"/posts/{post_id}/attachments/{att_id}", headers=_auth(token)
    )
    assert resp.status_code == 204
    assert len(storage.objects) == 0
    assert client.get(f"/posts/{post_id}/attachments").json() == []


def test_delete_attachment_other_user_403(
    client: TestClient, db_session: Session
) -> None:
    board = _board(db_session, slug="g")
    owner = _token(client, db_session, "owner@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(owner),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    other = _token(client, db_session, "other@example.com")
    resp = client.delete(f"/posts/{post_id}/attachments/{att_id}", headers=_auth(other))
    assert resp.status_code == 403


# ---- pending rows are not served (A-03) ----


def test_pending_attachment_not_listed(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "u@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    # inject a stray PENDING attachment directly
    db_session.add(
        Attachment(
            post_id=post_id,
            storage_key="att/orphan",
            original_name="x",
            content_type="text/plain",
            size=1,
            is_image=False,
            thumbnail_key=None,
            status=ContentStatus.PENDING,
        )
    )
    db_session.commit()
    atts = client.get(f"/posts/{post_id}/attachments").json()
    assert all(a["original_name"] != "x" for a in atts)
    assert len(atts) == 1


# ---- RV4 review-fix tests ----


def test_validate_rejects_declared_mime_mismatch() -> None:
    # RV4-003: PNG body declared as image/jpeg must be rejected.
    with pytest.raises(ValidationFailedError):
        validate_upload(
            data=_png_bytes(),
            declared_content_type="image/jpeg",
            require_image=True,
            filename="pic.png",
        )


def test_validate_rejects_extension_mismatch() -> None:
    # RV4-003: PNG body with .jpg extension must be rejected.
    with pytest.raises(ValidationFailedError):
        validate_upload(
            data=_png_bytes(),
            declared_content_type="image/png",
            require_image=True,
            filename="pic.jpg",
        )


def test_oversized_upload_rejected_413(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient, monkeypatch
) -> None:
    # RV4-002: oversized file rejected before storage/DB staging.
    settings = get_settings()
    monkeypatch.setattr(settings, "max_file_bytes", 10)
    monkeypatch.setattr(settings, "max_image_bytes", 10)
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("big.txt", b"x" * 100, "text/plain"))],
    )
    assert resp.status_code == 413
    assert len(storage.objects) == 0


def test_storage_failure_returns_502_and_keeps_pending(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    # RV4-001: storage upload failure surfaces as 5xx; PENDING rows retained (A-03 step 4).
    def _boom(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("s3 down")

    monkeypatch.setattr(InMemoryStorageClient, "put_object", _boom)
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "u@example.com")
    resp = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    )
    assert resp.status_code == 502
    # PENDING attachment row retained for the reconciliation job
    pending = [a for a in db_session.query(Attachment).all() if a.status == ContentStatus.PENDING]
    assert len(pending) == 1


def test_delete_with_wrong_post_id_404(
    client: TestClient, db_session: Session, storage: InMemoryStorageClient
) -> None:
    # RV4-005: nested route post_id must match the attachment's post.
    board = _board(db_session, slug="g")
    token = _token(client, db_session, "owner@example.com")
    post_id = client.post(
        f"/boards/{board.id}/posts/with-attachments",
        headers=_auth(token),
        data={"title": "t", "content": "c"},
        files=[("files", ("n.txt", b"data", "text/plain"))],
    ).json()["id"]
    att_id = client.get(f"/posts/{post_id}/attachments").json()[0]["id"]
    resp = client.delete(f"/posts/999999/attachments/{att_id}", headers=_auth(token))
    assert resp.status_code == 404
    assert len(storage.objects) == 1  # not deleted
