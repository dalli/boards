"""Attachment domain logic (AC4, A-02/A-03, NV2-002, E-01).

Upload is backend-mediated (A-02): the service validates bytes, writes a PENDING row,
uploads to S3, then flips to COMMITTED (ADR-0005). Download returns a short-lived presigned
GET gated by read_visibility (S-06). Delete removes the S3 object BEFORE the DB row (NV2-002)
and enforces the IMAGE "at least one image" invariant (E-01).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import NotFoundError, StorageError, ValidationFailedError
from app.models import Attachment, BoardType, ContentStatus, Post, User
from app.repository.attachment_repository import AttachmentRepository
from app.repository.board_repository import BoardRepository
from app.repository.post_repository import PostRepository
from app.service.file_validation import generate_storage_key, validate_upload
from app.service.image_service import make_thumbnail
from app.service.permissions import (
    ensure_can_read_board,
    ensure_can_write_board,
    ensure_owner_or_admin,
)
from app.storage import StorageClient


@dataclass
class UploadFile:
    filename: str
    content_type: str
    data: bytes


class AttachmentService:
    def __init__(self, db: Session, storage: StorageClient) -> None:
        self.db = db
        self.storage = storage
        self.attachments = AttachmentRepository(db)
        self.posts = PostRepository(db)
        self.boards = BoardRepository(db)

    # ---- create post with attachments (AC4; image-board path is Phase 5/AC5) ----

    def create_post_with_attachments(
        self,
        *,
        board_id: int,
        author: User,
        title: str,
        content: str,
        files: list[UploadFile],
    ) -> Post:
        board = self.boards.get_by_id(board_id)
        if board is None:
            raise NotFoundError("Board not found")
        ensure_can_write_board(board, author)

        require_image = board.type is BoardType.IMAGE
        # E-01: image boards require at least one image on creation.
        if require_image and not files:
            raise ValidationFailedError("Image board posts require at least one image")

        settings = get_settings()
        # A-03 step 1: create post + attachments PENDING first.
        post = self.posts.create(
            board_id=board_id,
            author_id=author.id,
            title=title,
            content=content,
            status=ContentStatus.PENDING,
        )

        staged: list[tuple[Attachment, bytes, bytes | None]] = []
        for f in files:
            is_image, effective_ct = validate_upload(
                data=f.data,
                declared_content_type=f.content_type,
                require_image=require_image,
                filename=f.filename,
            )
            storage_key = generate_storage_key()
            thumb_bytes: bytes | None = None
            thumbnail_key: str | None = None
            if is_image:
                thumb_bytes = make_thumbnail(f.data)
                thumbnail_key = generate_storage_key(prefix="thumb")
            attachment = self.attachments.create_pending(
                post_id=post.id,
                storage_key=storage_key,
                original_name=f.filename,
                content_type=effective_ct,
                size=len(f.data),
                is_image=is_image,
                thumbnail_key=thumbnail_key,
            )
            staged.append((attachment, f.data, thumb_bytes))

        # A-03 step 2: upload objects to S3. On failure, PENDING rows remain for the
        # reconciliation job to reclaim (no compensating rollback — data.md step 4).
        try:
            for attachment, raw, thumb in staged:
                self.storage.put_object(
                    bucket=settings.s3_bucket_attachments,
                    key=attachment.storage_key,
                    data=raw,
                    content_type=attachment.content_type,
                )
                if thumb is not None and attachment.thumbnail_key is not None:
                    self.storage.put_object(
                        bucket=settings.s3_bucket_thumbnails,
                        key=attachment.thumbnail_key,
                        data=thumb,
                        content_type="image/jpeg",
                    )
        except Exception as exc:  # noqa: BLE001 - surface storage failure as 5xx, keep PENDING
            self.db.commit()  # persist PENDING rows for the cleanup job (data.md step 4)
            raise StorageError("Upload to storage failed") from exc

        # A-03 step 3: single transaction flips post + attachments to COMMITTED.
        post.status = ContentStatus.COMMITTED
        for attachment, _, _ in staged:
            self.attachments.mark_committed(attachment)
        self.db.commit()
        self.db.refresh(post)
        return post

    # ---- list / download (AC4, AC6 original-url) ----

    def list_attachments(self, *, post_id: int, viewer: User | None) -> list[Attachment]:
        post = self._readable_post(post_id, viewer)
        return self.attachments.list_committed_for_post(post.id)

    def get_original_url(self, *, attachment_id: int, viewer: User | None) -> str:
        attachment = self._committed_attachment(attachment_id)
        post = self._readable_post(attachment.post_id, viewer)
        assert post is not None
        settings = get_settings()
        return self.storage.presigned_get_url(
            bucket=settings.s3_bucket_attachments,
            key=attachment.storage_key,
            expires_in=settings.presigned_ttl_seconds,
        )

    def get_thumbnail_url(self, attachment: Attachment) -> str | None:
        if attachment.thumbnail_key is None:
            return None
        settings = get_settings()
        return self.storage.presigned_get_url(
            bucket=settings.s3_bucket_thumbnails,
            key=attachment.thumbnail_key,
            expires_in=settings.presigned_ttl_seconds,
        )

    # ---- delete (NV2-002 S3-first, E-01 invariant) ----

    def delete_attachment(self, *, post_id: int, attachment_id: int, actor: User) -> None:
        attachment = self.attachments.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found")
        # RV4-005: bind the nested route's post_id to the attachment's actual post.
        if attachment.post_id != post_id:
            raise NotFoundError("Attachment not found")
        post = self.posts.get_by_id(attachment.post_id)
        if post is None:
            raise NotFoundError("Post not found")
        ensure_owner_or_admin(actor, post.author_id)

        board = self.boards.get_by_id(post.board_id)
        if board is None:
            raise NotFoundError("Board not found")
        # E-01: deleting the last image of an IMAGE-board post is rejected.
        if board.type is BoardType.IMAGE and attachment.is_image:
            remaining = self.attachments.count_committed_images(post.id)
            if remaining <= 1:
                raise ValidationFailedError(
                    "Image board posts must keep at least one image"
                )

        settings = get_settings()
        # NV2-002: delete S3 objects BEFORE the DB row so a crash never leaves an orphaned
        # DB row pointing at a missing object; a failed S3 delete leaves the row for cleanup.
        self.storage.delete_object(
            bucket=settings.s3_bucket_attachments, key=attachment.storage_key
        )
        if attachment.thumbnail_key is not None:
            self.storage.delete_object(
                bucket=settings.s3_bucket_thumbnails, key=attachment.thumbnail_key
            )
        self.attachments.delete(attachment)
        self.db.commit()

    # ---- helpers ----

    def _readable_post(self, post_id: int, viewer: User | None) -> Post:
        post = self.posts.get_by_id(post_id)
        if post is None or post.status is not ContentStatus.COMMITTED:
            raise NotFoundError("Post not found")
        board = self.boards.get_by_id(post.board_id)
        if board is None:
            raise NotFoundError("Board not found")
        ensure_can_read_board(board, viewer)
        return post

    def _committed_attachment(self, attachment_id: int) -> Attachment:
        attachment = self.attachments.get_by_id(attachment_id)
        if attachment is None or attachment.status is not ContentStatus.COMMITTED:
            raise NotFoundError("Attachment not found")
        return attachment
