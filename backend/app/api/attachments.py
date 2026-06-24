"""Attachment routes (AC4): backend-mediated upload, presigned download, delete.

Post creation WITH attachments uses multipart/form-data here; the JSON post-create route
(no attachments) stays in api/posts.py. Both produce a COMMITTED post.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.config import get_settings
from app.deps import CurrentUser, DbSession, OptionalUser, Storage
from app.errors import PayloadTooLargeError
from app.schemas import AttachmentResponse, OriginalUrlResponse, PostResponse
from app.service.attachment_service import AttachmentService
from app.service.attachment_service import UploadFile as ServiceUploadFile

router = APIRouter(tags=["attachments"])


async def _read_capped(upload: UploadFile, cap: int) -> bytes:
    """Read at most `cap` bytes; reject before buffering an oversized file (RV4-002, S-03).

    Uses the multipart-reported size when available, and also guards the actual read so a
    spoofed/absent size header cannot bypass the cap.
    """
    if upload.size is not None and upload.size > cap:
        raise PayloadTooLargeError("Uploaded file exceeds size limit")
    # Read cap+1 bytes; if we got more than cap, it is over the limit.
    data = await upload.read(cap + 1)
    if len(data) > cap:
        raise PayloadTooLargeError("Uploaded file exceeds size limit")
    return data


def _to_response(service: AttachmentService, att) -> AttachmentResponse:  # type: ignore[no-untyped-def]
    resp = AttachmentResponse.model_validate(att)
    resp.thumbnail_url = service.get_thumbnail_url(att)
    return resp


@router.post(
    "/boards/{board_id}/posts/with-attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=PostResponse,
)
async def create_post_with_attachments(
    board_id: int,
    db: DbSession,
    storage: Storage,
    author: CurrentUser,
    title: Annotated[str, Form(min_length=1, max_length=300)],
    content: Annotated[str, Form(min_length=1)],
    files: Annotated[list[UploadFile], File()] = [],  # noqa: B006 - FastAPI Form default
) -> PostResponse:
    settings = get_settings()
    # Hard cap = the larger of the two limits; the service re-checks the precise per-type cap
    # against the buffered bytes (RV4-002 prevents buffering arbitrarily large files here).
    hard_cap = max(settings.max_image_bytes, settings.max_file_bytes)
    service_files = [
        ServiceUploadFile(
            filename=f.filename or "upload",
            content_type=f.content_type or "application/octet-stream",
            data=await _read_capped(f, hard_cap),
        )
        for f in files
    ]
    post = AttachmentService(db, storage).create_post_with_attachments(
        board_id=board_id, author=author, title=title, content=content, files=service_files
    )
    return PostResponse.model_validate(post)


@router.get("/posts/{post_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(
    post_id: int, db: DbSession, storage: Storage, viewer: OptionalUser
) -> list[AttachmentResponse]:
    service = AttachmentService(db, storage)
    attachments = service.list_attachments(post_id=post_id, viewer=viewer)
    return [_to_response(service, a) for a in attachments]


@router.get("/attachments/{attachment_id}/original-url", response_model=OriginalUrlResponse)
def get_original_url(
    attachment_id: int, db: DbSession, storage: Storage, viewer: OptionalUser
) -> OriginalUrlResponse:
    url = AttachmentService(db, storage).get_original_url(
        attachment_id=attachment_id, viewer=viewer
    )
    return OriginalUrlResponse(url=url)


@router.delete(
    "/posts/{post_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_attachment(
    post_id: int, attachment_id: int, db: DbSession, storage: Storage, actor: CurrentUser
) -> None:
    AttachmentService(db, storage).delete_attachment(
        post_id=post_id, attachment_id=attachment_id, actor=actor
    )
