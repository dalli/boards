"""Phase 3 (AC9 / E-06): keyset cursor pagination boundary tests."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.errors import ValidationFailedError
from app.models import Board, BoardType, ContentStatus, Post, ReadVisibility
from app.service.pagination import MAX_LIMIT, clamp_limit, decode_cursor, encode_cursor


def _board(db: Session) -> Board:
    b = Board(
        name="B", slug="g", type=BoardType.GENERAL, read_visibility=ReadVisibility.PUBLIC,
        description=None,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _seed_posts(db: Session, board_id: int, n: int) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(n):
        db.add(
            Post(
                board_id=board_id,
                author_id=1,
                title=f"p{i}",
                content="c",
                status=ContentStatus.COMMITTED,
                created_at=base + timedelta(seconds=i),
            )
        )
    db.commit()


# ---- unit: clamp + cursor codec ----


def test_clamp_limit_defaults_and_caps() -> None:
    assert clamp_limit(None) == 20
    assert clamp_limit(5) == 5
    assert clamp_limit(10_000) == MAX_LIMIT


def test_cursor_roundtrip() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    token = encode_cursor(now, 42)
    dt, item_id = decode_cursor(token)
    assert dt == now and item_id == 42


# ---- integration: list boundaries ----


def test_empty_list_has_null_cursor(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    resp = client.get(f"/boards/{board.id}/posts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


def test_exactly_limit_has_null_cursor(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    _seed_posts(db_session, board.id, 3)
    resp = client.get(f"/boards/{board.id}/posts?limit=3")
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["next_cursor"] is None


def test_limit_plus_one_paginates(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    _seed_posts(db_session, board.id, 4)
    first = client.get(f"/boards/{board.id}/posts?limit=3").json()
    assert len(first["items"]) == 3
    assert first["next_cursor"] is not None
    # newest first → titles p3,p2,p1 on first page
    assert [i["title"] for i in first["items"]] == ["p3", "p2", "p1"]
    second = client.get(
        f"/boards/{board.id}/posts?limit=3&cursor={first['next_cursor']}"
    ).json()
    assert [i["title"] for i in second["items"]] == ["p0"]
    assert second["next_cursor"] is None


def test_no_duplicates_or_gaps_across_pages(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    _seed_posts(db_session, board.id, 7)
    seen: list[str] = []
    cursor = None
    for _ in range(10):
        url = f"/boards/{board.id}/posts?limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        page = client.get(url).json()
        seen.extend(i["title"] for i in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == [f"p{i}" for i in range(6, -1, -1)]  # p6..p0, no dup/gap


def test_limit_over_cap_clamped(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    _seed_posts(db_session, board.id, 5)
    # Request above MAX_LIMIT is clamped server-side (not rejected); 5 posts < cap → all return.
    resp = client.get(f"/boards/{board.id}/posts?limit=99999")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 5
    assert resp.json()["next_cursor"] is None


def test_clamp_limit_caps_query_to_max() -> None:
    assert clamp_limit(99999) == MAX_LIMIT


def test_invalid_cursor_422(client: TestClient, db_session: Session) -> None:
    board = _board(db_session)
    _seed_posts(db_session, board.id, 2)
    resp = client.get(f"/boards/{board.id}/posts?cursor=not-valid-base64!!")
    assert resp.status_code == 422


def test_malformed_base64_cursor_422(client: TestClient, db_session: Session) -> None:
    # F-004: base64 padding errors must surface as a controlled 422, not a 500.
    board = _board(db_session)
    _seed_posts(db_session, board.id, 2)
    resp = client.get(f"/boards/{board.id}/posts?cursor=abc")  # bad padding length
    assert resp.status_code == 422


def test_decode_cursor_raises_validation_on_bad_padding() -> None:
    with pytest.raises(ValidationFailedError):
        decode_cursor("abc")  # not valid base64 padding
