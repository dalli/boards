"""Board domain logic (AC2, AC3 write side).

Board create/delete are ADMIN-only (security.md). Read of a single board honors
read_visibility (E-04). Listing boards returns only metadata (no content), so it is
public — clients still cannot read posts in an AUTHENTICATED board without a token.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Board, BoardType, ReadVisibility, Role, User
from app.repository.board_repository import BoardRepository
from app.service.permissions import ensure_can_read_board


class BoardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.boards = BoardRepository(db)

    def create_board(
        self,
        *,
        actor: User,
        name: str,
        slug: str,
        type: BoardType,
        read_visibility: ReadVisibility,
        description: str | None,
    ) -> Board:
        if actor.role is not Role.ADMIN:
            raise PermissionDeniedError("Only admins can create boards")
        if self.boards.get_by_slug(slug) is not None:
            raise ConflictError("Board slug already exists")
        try:
            board = self.boards.create(
                name=name,
                slug=slug,
                type=type,
                read_visibility=read_visibility,
                description=description,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Board slug already exists") from exc
        self.db.refresh(board)
        return board

    def list_boards(self, viewer: User | None) -> list[Board]:
        # FINDING-001: anonymous users see only PUBLIC boards; authenticated users see all.
        # Listing AUTHENTICATED board metadata to anonymous viewers is a read they are not
        # authorized for (security.md E-04).
        if viewer is None:
            return self.boards.list_public()
        return self.boards.list_all()

    def get_board_for_read(self, board_id: int, viewer: User | None) -> Board:
        board = self.boards.get_by_id(board_id)
        if board is None:
            raise NotFoundError("Board not found")
        ensure_can_read_board(board, viewer)
        return board

    def get_board_for_write(self, board_id: int) -> Board:
        board = self.boards.get_by_id(board_id)
        if board is None:
            raise NotFoundError("Board not found")
        return board

    def delete_board(self, *, actor: User, board_id: int) -> None:
        if actor.role is not Role.ADMIN:
            raise PermissionDeniedError("Only admins can delete boards")
        board = self.boards.get_by_id(board_id)
        if board is None:
            raise NotFoundError("Board not found")
        # E-03: cascade cleanup of posts/comments/attachments (incl. S3) lands in Phase 3/4;
        # FKs are RESTRICT, so deletion of a non-empty board will fail until that cascade exists.
        self.boards.delete(board)
        self.db.commit()
