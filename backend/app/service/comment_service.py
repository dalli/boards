"""Comment domain logic (AC3 read, AC7).

Reading comments requires read access to the parent post's board (read_visibility).
Creating requires authentication (any authenticated user may comment on a readable post).
Editing/deleting requires owner-or-admin.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Comment, ContentStatus, User
from app.repository.board_repository import BoardRepository
from app.repository.comment_repository import CommentRepository
from app.repository.post_repository import PostRepository
from app.service.permissions import ensure_can_read_board, ensure_owner_or_admin


class CommentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.comments = CommentRepository(db)
        self.posts = PostRepository(db)
        self.boards = BoardRepository(db)

    def _readable_post(self, post_id: int, viewer: User | None):  # type: ignore[no-untyped-def]
        post = self.posts.get_by_id(post_id)
        if post is None or post.status is not ContentStatus.COMMITTED:
            raise NotFoundError("Post not found")
        board = self.boards.get_by_id(post.board_id)
        if board is None:
            raise NotFoundError("Board not found")
        ensure_can_read_board(board, viewer)
        return post

    def list_comments(self, *, post_id: int, viewer: User | None) -> list[Comment]:
        self._readable_post(post_id, viewer)
        return self.comments.list_for_post(post_id)

    def create_comment(self, *, post_id: int, author: User, content: str) -> Comment:
        self._readable_post(post_id, author)
        comment = self.comments.create(post_id=post_id, author_id=author.id, content=content)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def update_comment(self, *, comment_id: int, actor: User, content: str) -> Comment:
        comment = self.comments.get_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        ensure_owner_or_admin(actor, comment.author_id)
        self.comments.update_content(comment, content)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, *, comment_id: int, actor: User) -> None:
        comment = self.comments.get_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        ensure_owner_or_admin(actor, comment.author_id)
        self.comments.delete(comment)
        self.db.commit()
