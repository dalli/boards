"""Upload validation (S-03).

Cross-checks declared content-type against magic-byte sniffing, enforces size limits,
and restricts images to a MIME whitelist. The server-generated storage key replaces the
client filename to prevent path traversal/overwrite.
"""
from __future__ import annotations

import uuid

from app.config import get_settings
from app.errors import ValidationFailedError

# Magic-byte signatures → canonical content type. Kept small/explicit on purpose.
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # WEBP: 'RIFF'....'WEBP' (further checked below)
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Acceptable filename extensions per sniffed MIME (RV4-003 extension cross-check).
_EXT_BY_MIME: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "image/gif": {".gif"},
}


def sniff_image_type(data: bytes) -> str | None:
    """Return the detected image MIME from magic bytes, or None if not a known image."""
    for signature, mime in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            if mime == "image/webp":
                # RIFF container — confirm the WEBP fourCC at offset 8.
                if len(data) >= 12 and data[8:12] == b"WEBP":
                    return "image/webp"
                continue
            return mime
    return None


def generate_storage_key(*, prefix: str = "att") -> str:
    """Server-generated opaque key (S-03: never trust the client filename)."""
    return f"{prefix}/{uuid.uuid4().hex}"


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def validate_upload(
    *, data: bytes, declared_content_type: str, require_image: bool, filename: str = ""
) -> tuple[bool, str]:
    """Validate an uploaded file (S-03: magic bytes + declared type + extension cross-check).

    Returns (is_image, effective_content_type). Raises ValidationFailedError on any failure.
    For image boards (require_image=True) the file MUST sniff as an allowed image type, and
    the declared content-type and filename extension must agree with the sniffed type.
    """
    settings = get_settings()
    if not data:
        raise ValidationFailedError("Empty file")

    sniffed = sniff_image_type(data)
    is_image = sniffed is not None

    # When the body sniffs as an image, the declared content type must not contradict it
    # (RV4-003 — a PNG body declared as image/jpeg is rejected).
    if sniffed is not None and declared_content_type and declared_content_type != sniffed:
        raise ValidationFailedError("Declared content type does not match file contents")

    # Extension cross-check for recognized images (RV4-003).
    if sniffed is not None and filename:
        ext = _extension(filename)
        if ext and ext not in _EXT_BY_MIME.get(sniffed, set()):
            raise ValidationFailedError("File extension does not match file contents")

    if require_image:
        if sniffed is None or sniffed not in ALLOWED_IMAGE_TYPES:
            raise ValidationFailedError("Image board accepts image files only")
        if len(data) > settings.max_image_bytes:
            raise ValidationFailedError("Image exceeds size limit")
        return True, sniffed

    # General file path
    size_cap = settings.max_image_bytes if is_image else settings.max_file_bytes
    if len(data) > size_cap:
        raise ValidationFailedError("File exceeds size limit")
    if sniffed is not None:
        effective = sniffed
    else:
        effective = declared_content_type or "application/octet-stream"
    return is_image, effective
