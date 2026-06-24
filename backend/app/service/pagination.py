"""Opaque keyset cursor encoding for list pagination (E-06).

Cursor = base64url(json([created_at_iso, id])). Opaque to clients; decoded server-side
into the (created_at, id) keyset boundary. limit default 20, hard cap 100.
"""
from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime

from app.errors import ValidationFailedError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1:
        raise ValidationFailedError("limit must be >= 1")
    return min(limit, MAX_LIMIT)


def encode_cursor(created_at: datetime, item_id: int) -> str:
    raw = json.dumps([created_at.isoformat(), item_id]).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(token: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        created_at_iso, item_id = json.loads(raw)
        return datetime.fromisoformat(created_at_iso), int(item_id)
    except (ValueError, TypeError, binascii.Error, UnicodeError) as exc:
        # binascii.Error: base64 padding/format; others: bad JSON shape / non-iso datetime (F-004).
        raise ValidationFailedError("Invalid cursor") from exc
