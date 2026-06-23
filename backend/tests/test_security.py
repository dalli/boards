"""Security unit tests for codex Phase-0+1 fixes (SEC-001, SEC-006, AUTH-002)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.config import Settings, get_settings
from app.errors import AuthenticationError
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_roundtrip() -> None:
    h = hash_password("a-very-long-password-" * 5)  # exceeds 72 bytes; must still work
    assert verify_password("a-very-long-password-" * 5, h)
    assert not verify_password("wrong", h)


def test_token_roundtrip() -> None:
    token = create_access_token(user_id=7, role="USER")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "USER"


def test_decode_rejects_token_without_exp() -> None:
    # SEC-001: a signed token lacking exp must be rejected, not treated as non-expiring.
    s = get_settings()
    bad = jwt.encode(
        {"sub": "1", "role": "USER", "iat": 1}, s.jwt_secret, algorithm=s.jwt_algorithm
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(bad)


def test_decode_rejects_expired_token() -> None:
    s = get_settings()
    past = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    expired = jwt.encode(
        {"sub": "1", "role": "USER", "iat": past - 60, "exp": past},
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(expired)


def test_config_rejects_weak_bcrypt_cost() -> None:
    # SEC-006: cost < 12 must be refused at config load.
    with pytest.raises(ValueError):
        Settings(bcrypt_rounds=8)


def test_config_accepts_strong_bcrypt_cost() -> None:
    assert Settings(bcrypt_rounds=12).bcrypt_rounds == 12
