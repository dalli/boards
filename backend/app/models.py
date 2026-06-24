"""ORM models — 1:1 with docs/architecture/db-schema.md.

Enums enforced via CHECK-backed SQLAlchemy Enum. FK delete behavior is explicit
per A-04 / NV2-002 (no blanket CASCADE); application enforces S3-before-DB ordering.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# BigInteger autoincrements as BIGSERIAL/identity on Postgres, but SQLite only
# autoincrements INTEGER PRIMARY KEY. This variant keeps BIGINT on Postgres while
# letting SQLite (used by unit tests) generate PKs.
PkInt = BigInteger().with_variant(Integer, "sqlite")


class Role(enum.StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class BoardType(enum.StrEnum):
    NOTICE = "NOTICE"
    GENERAL = "GENERAL"
    IMAGE = "IMAGE"


class ReadVisibility(enum.StrEnum):
    PUBLIC = "PUBLIC"
    AUTHENTICATED = "AUTHENTICATED"


class ContentStatus(enum.StrEnum):
    """A-03 / ADR-0005: only COMMITTED rows are served to users."""

    PENDING = "PENDING"
    COMMITTED = "COMMITTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PkInt, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role"), nullable=False, default=Role.USER, server_default=Role.USER.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # ADR-0006: soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # NV2-003: partial unique on active users only
        Index("uq_users_email_active", "email", unique=True, postgresql_where=deleted_at.is_(None)),
    )


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(PkInt, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    type: Mapped[BoardType] = mapped_column(Enum(BoardType, name="board_type"), nullable=False)
    read_visibility: Mapped[ReadVisibility] = mapped_column(
        Enum(ReadVisibility, name="read_visibility"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    posts: Mapped[list[Post]] = relationship(back_populates="board")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(PkInt, primary_key=True)
    board_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status"),
        nullable=False,
        default=ContentStatus.PENDING,
        server_default=ContentStatus.PENDING.value,
    )
    # E-05: optimistic lock
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    board: Mapped[Board] = relationship(back_populates="posts")
    attachments: Mapped[list[Attachment]] = relationship(back_populates="post")
    comments: Mapped[list[Comment]] = relationship(back_populates="post")

    __table_args__ = (
        # E-06 keyset cursor pagination coverage
        Index(
            "ix_posts_board_status_created_id",
            "board_id",
            "status",
            created_at.desc(),
            id.desc(),
        ),
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(PkInt, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_image: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=func.false()
    )
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status"),
        nullable=False,
        default=ContentStatus.PENDING,
        server_default=ContentStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped[Post] = relationship(back_populates="attachments")

    __table_args__ = (
        # A-05: partial unique on thumbnail_key when present
        Index(
            "uq_attachments_thumbnail_key",
            "thumbnail_key",
            unique=True,
            postgresql_where=thumbnail_key.isnot(None),
        ),
        Index("ix_attachments_post", "post_id"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(PkInt, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped[Post] = relationship(back_populates="comments")

    __table_args__ = (Index("ix_comments_post_created", "post_id", "created_at"),)
