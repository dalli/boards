"""Board persistence (§5 — only place boards are read/written via SQLAlchemy)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Board, BoardType, ReadVisibility


class BoardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, board_id: int) -> Board | None:
        return self.db.get(Board, board_id)

    def get_by_slug(self, slug: str) -> Board | None:
        return self.db.scalar(select(Board).where(Board.slug == slug))

    def list_all(self) -> list[Board]:
        stmt = select(Board).order_by(Board.created_at.desc(), Board.id.desc())
        return list(self.db.scalars(stmt))

    def list_public(self) -> list[Board]:
        stmt = (
            select(Board)
            .where(Board.read_visibility == ReadVisibility.PUBLIC)
            .order_by(Board.created_at.desc(), Board.id.desc())
        )
        return list(self.db.scalars(stmt))

    def create(
        self,
        *,
        name: str,
        slug: str,
        type: BoardType,
        read_visibility: ReadVisibility,
        description: str | None,
    ) -> Board:
        board = Board(
            name=name,
            slug=slug,
            type=type,
            read_visibility=read_visibility,
            description=description,
        )
        self.db.add(board)
        self.db.flush()
        return board

    def delete(self, board: Board) -> None:
        self.db.delete(board)
        self.db.flush()
