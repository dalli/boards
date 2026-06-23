"""Password hashing and JWT helpers (S-02: HS256, 30-min TTL, fixed alg).

bcrypt cost >= 12. JWT secret is injected via settings (never committed). The api layer
never trusts the token's role blindly — service re-checks against the DB (security.md).
"""
from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.errors import AuthenticationError


def _prepare(plain: str) -> bytes:
    # bcrypt operates on the first 72 bytes only. Pre-hash with SHA-256 then base64 so
    # arbitrarily long passwords are fully mixed in (avoids silent truncation).
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    settings = get_settings()
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(_prepare(plain), salt).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), password_hash.encode("ascii"))
    except ValueError:
        return False


# Pre-computed hash used to verify against when no user matches, so login spends roughly
# the same time whether or not the account exists (mitigates the timing side channel, SEC-004).
DUMMY_PASSWORD_HASH = bcrypt.hashpw(_prepare("dummy-password"), bcrypt.gensalt(rounds=12)).decode(
    "ascii"
)


def create_access_token(*, user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        # alg pinned to prevent algorithm-confusion attacks (S-02).
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    # python-jose validates exp when present but does not *require* it; enforce required
    # claims explicitly so a token missing expiry/subject is rejected (SEC-001).
    for claim in ("exp", "iat", "sub"):
        if claim not in payload:
            raise AuthenticationError("Token missing required claim")
    return payload
