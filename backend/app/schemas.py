"""Pydantic request/response schemas — the OpenAPI contract surface (§5.1, SoT=backend)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BoardType, ContentStatus, ReadVisibility, Role

# ---- Auth / User ----


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    created_at: datetime


# ---- Board ----


class BoardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9][a-z0-9-]*$")
    type: BoardType
    read_visibility: ReadVisibility
    description: str | None = Field(default=None, max_length=2000)


class BoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    type: BoardType
    read_visibility: ReadVisibility
    description: str | None
    created_at: datetime


# ---- Post ----


class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class PostUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    version: int = Field(ge=0)  # E-05 optimistic lock


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    author_id: int
    title: str
    content: str
    status: ContentStatus
    version: int
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    items: list[PostResponse]
    next_cursor: str | None = None


# ---- Comment ----


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime


# ---- Attachment ----


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    original_name: str
    content_type: str
    size: int
    is_image: bool
    # presigned thumbnail URL (images only); populated by the service, not the ORM
    thumbnail_url: str | None = None


class OriginalUrlResponse(BaseModel):
    url: str


class PostDetailResponse(BaseModel):
    """Post GET response including committed attachments with thumbnail URLs (AC6 grid)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    author_id: int
    title: str
    content: str
    status: ContentStatus
    version: int
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentResponse] = []
