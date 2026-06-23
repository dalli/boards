"""Image processing (S-03 hardening + thumbnail generation).

Decodes with Pillow under a decompression-bomb guard, re-encodes to neutralize malicious
payloads, and generates a bounded thumbnail. Returns raw bytes; storage is the caller's job.
"""
from __future__ import annotations

import io

from app.config import get_settings
from app.errors import ValidationFailedError


def _load_pillow():  # type: ignore[no-untyped-def]
    from PIL import Image

    settings = get_settings()
    # Decompression-bomb guard: cap decoded pixel count (S-03).
    Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
    return Image


def make_thumbnail(data: bytes) -> bytes:
    """Generate a JPEG thumbnail bounded by settings.thumbnail_max_px on the long edge.

    Decoding validates the image; a corrupt/oversized image raises ValidationFailedError.
    """
    Image = _load_pillow()
    from PIL import Image as PILImage

    settings = get_settings()
    try:
        with PILImage.open(io.BytesIO(data)) as img:
            img.verify()  # detect truncated/corrupt files
        # verify() leaves the image unusable; reopen for processing.
        with PILImage.open(io.BytesIO(data)) as img:
            # Explicit pixel-count cap (RV4-004): don't rely on Pillow's 2x bomb threshold.
            width, height = img.size
            if width * height > settings.max_image_pixels:
                raise ValidationFailedError("Image dimensions exceed the allowed pixel limit")
            rgb = img.convert("RGB")
            rgb.thumbnail((settings.thumbnail_max_px, settings.thumbnail_max_px))
            out = io.BytesIO()
            rgb.save(out, format="JPEG", quality=85)
            return out.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationFailedError("Invalid or unprocessable image") from exc
