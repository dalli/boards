"""initial schema: users, boards, posts, attachments, comments

Revision ID: 0001
Revises:
Create Date: 2026-06-23

Matches docs/architecture/db-schema.md: partial unique indexes (NV2-003, A-05),
explicit FK delete behavior (A-04 / NV2-002), keyset pagination index (E-06).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

role_enum = sa.Enum("USER", "ADMIN", name="role")
board_type_enum = sa.Enum("NOTICE", "GENERAL", "IMAGE", name="board_type")
read_visibility_enum = sa.Enum("PUBLIC", "AUTHENTICATED", name="read_visibility")
content_status_enum = sa.Enum("PENDING", "COMMITTED", name="content_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="USER"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # NV2-003: unique only among active users
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "boards",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("type", board_type_enum, nullable=False),
        sa.Column("read_visibility", read_visibility_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("board_id", sa.BigInteger(), sa.ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", content_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # E-06 keyset pagination cover index
    op.create_index(
        "ix_posts_board_status_created_id",
        "posts",
        ["board_id", "status", sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("original_name", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("is_image", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("thumbnail_key", sa.String(512), nullable=True),
        sa.Column("status", content_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # A-05: partial unique on thumbnail_key when present
    op.create_index(
        "uq_attachments_thumbnail_key",
        "attachments",
        ["thumbnail_key"],
        unique=True,
        postgresql_where=sa.text("thumbnail_key IS NOT NULL"),
    )
    op.create_index("ix_attachments_post", "attachments", ["post_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_comments_post_created", "comments", ["post_id", "created_at"])


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_index("ix_attachments_post", table_name="attachments")
    op.drop_index("uq_attachments_thumbnail_key", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_posts_board_status_created_id", table_name="posts")
    op.drop_table("posts")
    op.drop_table("boards")
    op.drop_index("uq_users_email_active", table_name="users")
    op.drop_table("users")
    content_status_enum.drop(op.get_bind(), checkfirst=True)
    read_visibility_enum.drop(op.get_bind(), checkfirst=True)
    board_type_enum.drop(op.get_bind(), checkfirst=True)
    role_enum.drop(op.get_bind(), checkfirst=True)
