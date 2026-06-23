"""Authentication domain logic (auth.md sequence).

Signup hashes with bcrypt; login excludes soft-deleted users (NV2-003) and returns a
generalized 401 to avoid account enumeration (S-05).
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AuthenticationError, ConflictError, NotFoundError, PermissionDeniedError
from app.models import Role, User
from app.repository.user_repository import UserRepository
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def signup(self, *, email: str, password: str) -> User:
        if self.users.get_active_by_email(email) is not None:
            raise ConflictError("Email already registered")
        try:
            user = self.users.create(email=email, password_hash=hash_password(password))
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Email already registered") from exc
        self.db.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> str:
        user = self.users.get_active_by_email(email)
        # Always run bcrypt — against the real hash if the user exists, else a dummy hash —
        # so timing does not reveal account existence (SEC-004). Single generalized error (S-05).
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_ok = verify_password(password, password_hash)
        if user is None or not password_ok:
            raise AuthenticationError("Invalid email or password")
        return create_access_token(user_id=user.id, role=user.role.value)

    def promote_to_admin(self, *, actor: User, target_user_id: int) -> User:
        # Defense in depth: service re-checks the ADMIN gate, not just the router (AUTH-001, §5).
        if actor.role is not Role.ADMIN:
            raise PermissionDeniedError("Admin privileges required")
        user = self.users.get_active_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found")
        self.users.set_role(user, Role.ADMIN)  # write via repository (LAY-001)
        self.db.commit()
        self.db.refresh(user)
        return user
