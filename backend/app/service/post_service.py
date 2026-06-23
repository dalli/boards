"""Post domain logic (AC3 read, AC7, AC9).

Authorization reuses service/permissions (read=read_visibility, write=Board.type,
edit/delete=owner-or-admin). Updates use optimistic locking via Post.version (E-05 → 409).
Listing is keyset cursor pagination over COMMITTED posts (E-06).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Board, ContentStatus, Post, User
from app.repository.board_repository import BoardRepository
from app.repository.post_repository import PostRepository
from app.service.pagination import clamp_limit, decode_cursor, encode_cursor
from app.service.permissions import (
    ensure_can_read_board,
    ensure_can_write_board,
    ensure_owner_or_admin,
)


class PostService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.posts = PostRepository(db)
        self.boards = BoardRepository(db)

    def _get_board_or_404(self, board_id: int) -> Board:
        board = self.boards.get_by_id(board_id)
        if board is None:
            raise NotFoundError("Board not found")
        return board

    def create_post(self, *, board_id: int, author: User, title: str, content: str) -> Post:
        board = self._get_board_or_404(board_id)
        ensure_can_write_board(board, author)
        # No attachments in Phase 3, so the post is COMMITTED immediately. Phase 4 introduces
        # the PENDING→COMMITTED lifecycle when attachments are present (A-03).
        post = self.posts.create(
            board_id=board_id,
            author_id=author.id,
            title=title,
            content=content,
            status=ContentStatus.COMMITTED,
        )
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_post(self, *, post_id: int, viewer: User | None) -> Post:
        post = self.posts.get_by_id(post_id)
        if post is None or post.status is not ContentStatus.COMMITTED:
            raise NotFoundError("Post not found")
        board = self._get_board_or_404(post.board_id)
        ensure_can_read_board(board, viewer)
        return post

    def list_posts(
        self, *, board_id: int, viewer: User | None, limit: int | None, cursor: str | None
    ) -> tuple[list[Post], str | None]:
        board = self._get_board_or_404(board_id)
        ensure_can_read_board(board, viewer)
        page_size = clamp_limit(limit)
        keyset = decode_cursor(cursor) if cursor else None
        # Fetch one extra to determine whether a next page exists.
        rows = self.posts.list_committed(board_id=board_id, limit=page_size + 1, cursor=keyset)
        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
        )
        return items, next_cursor

    def update_post(
        self, *, post_id: int, actor: User, title: str, content: str, client_version: int
    ) -> Post:
        post = self.posts.get_by_id(post_id)
        if post is None or post.status is not ContentStatus.COMMITTED:
            raise NotFoundError("Post not found")
        ensure_owner_or_admin(actor, post.author_id)
        # F-002: re-apply the board write gate on update (defense in depth) so a NOTICE post
        # can only ever be modified by an ADMIN, independent of authorship.
        board = self._get_board_or_404(post.board_id)
        ensure_can_write_board(board, actor)
        # E-05 optimistic lock, done atomically (F-001): UPDATE ... WHERE version=expected.
        # rowcount==0 means another writer bumped the version first → 409.
        updated = self.posts.update_if_version(
            post_id=post_id, expected_version=client_version, title=title, content=content
        )
        if updated == 0:
            self.db.rollback()
            raise ConflictError("Post was modified by someone else; refresh and retry")
        self.db.commit()
        refreshed = self.posts.get_by_id(post_id)
        assert refreshed is not None  # just updated within this transaction
        return refreshed

    def delete_post(self, *, post_id: int, actor: User) -> None:
        post = self.posts.get_by_id(post_id)
        if post is None:
            raise NotFoundError("Post not found")
        ensure_owner_or_admin(actor, post.author_id)
        # NV-002: re-apply the board write gate on delete too (symmetry with update) so a
        # NOTICE post can only be removed by an ADMIN, regardless of recorded authorship.
        board = self._get_board_or_404(post.board_id)
        ensure_can_write_board(board, actor)
        # Comments cascade via FK ON DELETE CASCADE. Attachment cleanup (S3-first) lands in
        # Phase 4; until then a post with attachments cannot be deleted (FK RESTRICT).
        self.posts.delete(post)
        self.db.commit()
