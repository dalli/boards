"""Centralized authorization rules (security.md §인가, E-04).

Two independent axes:
  - READ  → Board.read_visibility (PUBLIC | AUTHENTICATED)
  - WRITE → Board.type (NOTICE → ADMIN only; GENERAL/IMAGE → any authenticated user)

These functions raise domain errors (no HTTP) so they compose in the service layer (§5).
Reused by board/post/attachment services for a single source of truth.
"""
from __future__ import annotations

from app.errors import AuthenticationError, PermissionDeniedError
from app.models import Board, BoardType, ReadVisibility, Role, User


def ensure_can_read_board(board: Board, viewer: User | None) -> None:
    """PUBLIC boards are readable by anyone; AUTHENTICATED requires a logged-in user."""
    if board.read_visibility is ReadVisibility.PUBLIC:
        return
    if viewer is None:
        # AUTHENTICATED board, no viewer → 401 (authenticate to read)
        raise AuthenticationError("Authentication required to read this board")


def ensure_can_write_board(board: Board, actor: User) -> None:
    """Write gate by board type. NOTICE is ADMIN-only; GENERAL/IMAGE allow any user."""
    if board.type is BoardType.NOTICE and actor.role is not Role.ADMIN:
        raise PermissionDeniedError("Only admins can post to a notice board")


def is_owner_or_admin(actor: User, author_id: int) -> bool:
    return actor.role is Role.ADMIN or actor.id == author_id


def ensure_owner_or_admin(actor: User, author_id: int) -> None:
    if not is_owner_or_admin(actor, author_id):
        raise PermissionDeniedError("Only the author or an admin may modify this resource")
