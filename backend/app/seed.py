"""Seed the initial ADMIN account (Y-02).

Password is read from SEED_ADMIN_PASSWORD env at runtime — never committed. Idempotent:
re-running with the same email leaves the existing active admin untouched.

Usage: SEED_ADMIN_PASSWORD=... python -m app.seed
"""
from __future__ import annotations

import sys

from app.config import get_settings
from app.db import SessionLocal
from app.models import Role
from app.repository.user_repository import UserRepository
from app.security import hash_password


def seed_admin() -> int:
    settings = get_settings()
    if not settings.seed_admin_password:
        print(
            "SEED_ADMIN_PASSWORD not set — refusing to seed with empty password.",
            file=sys.stderr,
        )
        return 1

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        existing = repo.get_active_by_email(settings.seed_admin_email)
        if existing is not None:
            if existing.role is not Role.ADMIN:
                existing.role = Role.ADMIN
                db.commit()
                print(f"Promoted existing user {settings.seed_admin_email} to ADMIN.")
            else:
                print(f"Admin {settings.seed_admin_email} already exists; nothing to do.")
            return 0
        repo.create(
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            role=Role.ADMIN,
        )
        db.commit()
        print(f"Created ADMIN {settings.seed_admin_email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(seed_admin())
