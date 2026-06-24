"""Board routes (AC2, AC3 write side). HTTP-layer only — delegates to BoardService (§5)."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import AdminUser, DbSession, OptionalUser
from app.schemas import BoardCreateRequest, BoardResponse
from app.service.board_service import BoardService

router = APIRouter(tags=["boards"])


@router.post("/admin/boards", status_code=status.HTTP_201_CREATED, response_model=BoardResponse)
def create_board(payload: BoardCreateRequest, db: DbSession, admin: AdminUser) -> BoardResponse:
    board = BoardService(db).create_board(
        actor=admin,
        name=payload.name,
        slug=payload.slug,
        type=payload.type,
        read_visibility=payload.read_visibility,
        description=payload.description,
    )
    return BoardResponse.model_validate(board)


@router.get("/boards", response_model=list[BoardResponse])
def list_boards(db: DbSession, viewer: OptionalUser) -> list[BoardResponse]:
    boards = BoardService(db).list_boards(viewer)
    return [BoardResponse.model_validate(b) for b in boards]


@router.get("/boards/{board_id}", response_model=BoardResponse)
def get_board(board_id: int, db: DbSession, viewer: OptionalUser) -> BoardResponse:
    board = BoardService(db).get_board_for_read(board_id, viewer)
    return BoardResponse.model_validate(board)


@router.delete("/admin/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int, db: DbSession, admin: AdminUser) -> None:
    BoardService(db).delete_board(actor=admin, board_id=board_id)
