"""Post persistence with keyset cursor pagination (E-06, §5).

Only COMMITTED posts are listed/served (A-03). Listing uses the
(created_at DESC, id DESC) keyset covered by ix_posts_board_status_created_id.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models import ContentStatus, Post


class PostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, post_id: int) -> Post | None:
        return self.db.get(Post, post_id)

    def create(
        self,
        *,
        board_id: int,
        author_id: int,
        title: str,
        content: str,
        status: ContentStatus = ContentStatus.COMMITTED,
    ) -> Post:
        post = Post(
            board_id=board_id,
            author_id=author_id,
            title=title,
            content=content,
            status=status,
        )
        self.db.add(post)
        self.db.flush()
        return post

    def delete(self, post: Post) -> None:
        self.db.delete(post)
        self.db.flush()

    def update_if_version(
        self, *, post_id: int, expected_version: int, title: str, content: str
    ) -> int:
        """Atomic optimistic update: UPDATE ... WHERE id=? AND version=? (F-001).

        Returns the number of rows updated (1 on success, 0 if the version was stale).
        The version-in-WHERE makes the check-and-set atomic at the DB level, so two
        concurrent updaters cannot both succeed.
        """
        stmt = (
            update(Post)
            .where(Post.id == post_id, Post.version == expected_version)
            .values(title=title, content=content, version=Post.version + 1)
        )
        result = self.db.execute(stmt)
        return result.rowcount  # type: ignore[attr-defined]  # CursorResult for UPDATE

    def list_committed(
        self,
        *,
        board_id: int,
        limit: int,
        cursor: tuple[datetime, int] | None = None,
    ) -> list[Post]:
        """Return up to `limit` COMMITTED posts after the cursor, newest first.

        Keyset condition: (created_at, id) < (cursor_created_at, cursor_id) under the
        (created_at DESC, id DESC) ordering — stable, no offset (E-06).
        """
        stmt = select(Post).where(
            Post.board_id == board_id,
            Post.status == ContentStatus.COMMITTED,
        )
        if cursor is not None:
            cursor_created_at, cursor_id = cursor
            # (created_at, id) < (cursor_created_at, cursor_id) under DESC ordering.
            # Expanded form (not row-value tuple) for portability across Postgres/SQLite.
            stmt = stmt.where(
                or_(
                    Post.created_at < cursor_created_at,
                    and_(Post.created_at == cursor_created_at, Post.id < cursor_id),
                )
            )
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))
