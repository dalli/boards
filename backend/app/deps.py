"""FastAPI dependencies for authn/authz.

Token role is NOT trusted — the user is re-loaded from the DB and the live role is used
(security.md). require_admin enforces the ADMIN gate at the edge; service layers re-check
ownership/role for defense in depth.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AuthenticationError, PermissionDeniedError
from app.models import Role, User
from app.repository.user_repository import UserRepository
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    user_id = _parse_subject(payload.get("sub"))
    user = UserRepository(db).get_active_by_id(user_id)
    if user is None:
        raise AuthenticationError("User no longer active")
    return user


def _parse_subject(sub: object) -> int:
    """Token subject must be an integer user id; reject anything else as auth failure (AUTH-002)."""
    if not isinstance(sub, (str, int)):
        raise AuthenticationError("Invalid token subject")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid token subject") from exc


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """For PUBLIC read endpoints: identifies the user if a valid token is present, else None."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = _parse_subject(payload.get("sub"))
        return UserRepository(db).get_active_by_id(user_id)
    except AuthenticationError:
        return None


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role is not Role.ADMIN:
        raise PermissionDeniedError("Admin privileges required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated["User | None", Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
DbSession = Annotated[Session, Depends(get_db)]
