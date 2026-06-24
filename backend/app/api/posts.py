"""Post & comment routes (AC3 read, AC7, AC9). HTTP-layer only (§5)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, DbSession, OptionalUser, Storage
from app.schemas import (
    AttachmentResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    PostCreateRequest,
    PostDetailResponse,
    PostListResponse,
    PostResponse,
    PostUpdateRequest,
)
from app.service.attachment_service import AttachmentService
from app.service.comment_service import CommentService
from app.service.post_service import PostService

router = APIRouter(tags=["posts"])


# ---- Posts ----


@router.post(
    "/boards/{board_id}/posts",
    status_code=status.HTTP_201_CREATED,
    response_model=PostResponse,
)
def create_post(
    board_id: int, payload: PostCreateRequest, db: DbSession, author: CurrentUser
) -> PostResponse:
    post = PostService(db).create_post(
        board_id=board_id, author=author, title=payload.title, content=payload.content
    )
    return PostResponse.model_validate(post)


@router.get("/boards/{board_id}/posts", response_model=PostListResponse)
def list_posts(
    board_id: int,
    db: DbSession,
    viewer: OptionalUser,
    limit: Annotated[int | None, Query(ge=1)] = None,
    cursor: str | None = None,
) -> PostListResponse:
    items, next_cursor = PostService(db).list_posts(
        board_id=board_id, viewer=viewer, limit=limit, cursor=cursor
    )
    return PostListResponse(
        items=[PostResponse.model_validate(p) for p in items], next_cursor=next_cursor
    )


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int, db: DbSession, storage: Storage, viewer: OptionalUser
) -> PostDetailResponse:
    post = PostService(db).get_post(post_id=post_id, viewer=viewer)
    # AC6: include committed attachments with presigned thumbnail URLs for the grid.
    att_service = AttachmentService(db, storage)
    attachments = att_service.list_attachments(post_id=post_id, viewer=viewer)
    detail = PostDetailResponse.model_validate(post)
    detail.attachments = []
    for a in attachments:
        resp = AttachmentResponse.model_validate(a)
        resp.thumbnail_url = att_service.get_thumbnail_url(a)
        detail.attachments.append(resp)
    return detail


@router.put("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int, payload: PostUpdateRequest, db: DbSession, actor: CurrentUser
) -> PostResponse:
    post = PostService(db).update_post(
        post_id=post_id,
        actor=actor,
        title=payload.title,
        content=payload.content,
        client_version=payload.version,
    )
    return PostResponse.model_validate(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: DbSession, actor: CurrentUser) -> None:
    PostService(db).delete_post(post_id=post_id, actor=actor)


# ---- Comments ----


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(post_id: int, db: DbSession, viewer: OptionalUser) -> list[CommentResponse]:
    comments = CommentService(db).list_comments(post_id=post_id, viewer=viewer)
    return [CommentResponse.model_validate(c) for c in comments]


@router.post(
    "/posts/{post_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
)
def create_comment(
    post_id: int, payload: CommentCreateRequest, db: DbSession, author: CurrentUser
) -> CommentResponse:
    comment = CommentService(db).create_comment(
        post_id=post_id, author=author, content=payload.content
    )
    return CommentResponse.model_validate(comment)


@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int, payload: CommentUpdateRequest, db: DbSession, actor: CurrentUser
) -> CommentResponse:
    comment = CommentService(db).update_comment(
        comment_id=comment_id, actor=actor, content=payload.content
    )
    return CommentResponse.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: DbSession, actor: CurrentUser) -> None:
    CommentService(db).delete_comment(comment_id=comment_id, actor=actor)
