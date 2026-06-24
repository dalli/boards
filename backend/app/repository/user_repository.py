"""User persistence — the only place users are read/written via SQLAlchemy (§5)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return self.db.scalar(stmt)

    def get_active_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        return self.db.scalar(stmt)

    def create(self, *, email: str, password_hash: str, role: Role = Role.USER) -> User:
        user = User(email=email, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.flush()
        return user

    def set_role(self, user: User, role: Role) -> User:
        user.role = role
        self.db.flush()
        return user
