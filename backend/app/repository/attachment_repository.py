"""Attachment persistence (§5). PENDING→COMMITTED lifecycle per ADR-0005."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attachment, ContentStatus


class AttachmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, attachment_id: int) -> Attachment | None:
        return self.db.get(Attachment, attachment_id)

    def list_committed_for_post(self, post_id: int) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(
                Attachment.post_id == post_id,
                Attachment.status == ContentStatus.COMMITTED,
            )
            .order_by(Attachment.id.asc())
        )
        return list(self.db.scalars(stmt))

    def count_committed_images(self, post_id: int) -> int:
        stmt = select(func.count()).where(
            Attachment.post_id == post_id,
            Attachment.status == ContentStatus.COMMITTED,
            Attachment.is_image.is_(True),
        )
        return int(self.db.scalar(stmt) or 0)

    def create_pending(
        self,
        *,
        post_id: int,
        storage_key: str,
        original_name: str,
        content_type: str,
        size: int,
        is_image: bool,
        thumbnail_key: str | None,
    ) -> Attachment:
        attachment = Attachment(
            post_id=post_id,
            storage_key=storage_key,
            original_name=original_name,
            content_type=content_type,
            size=size,
            is_image=is_image,
            thumbnail_key=thumbnail_key,
            status=ContentStatus.PENDING,
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def mark_committed(self, attachment: Attachment) -> None:
        attachment.status = ContentStatus.COMMITTED
        self.db.flush()

    def delete(self, attachment: Attachment) -> None:
        self.db.delete(attachment)
        self.db.flush()
