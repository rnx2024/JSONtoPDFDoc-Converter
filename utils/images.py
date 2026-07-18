import base64
import os

from fastapi import UploadFile

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_READ_CHUNK_BYTES = 65536

DEFAULT_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

ALLOWED_IMAGE_EXTENSIONS = set(DEFAULT_MIME_BY_EXTENSION)


class ImageValidationError(ValueError):
    """Raised when an uploaded image fails extension, signature, or size checks."""


def _matches_signature(ext: str, data: bytes) -> bool:
    if ext in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext == ".svg":
        head = data[:256].lstrip().lower()
        return head.startswith(b"<svg") or head.startswith(b"<?xml")
    return False


async def _read_bounded(image: UploadFile, max_bytes: int) -> bytes:
    # image.read() is Starlette's async-safe read -- it's dispatched to a
    # worker thread internally, so this doesn't block the event loop the way
    # calling image.file.read() directly would.
    chunks = []
    total = 0
    while True:
        chunk = await image.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ImageValidationError(f"Image exceeds maximum size of {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


async def validate_and_read_image(
    image: UploadFile | None,
) -> tuple[bytes | None, str | None, str | None, str | None]:
    if not image:
        return None, None, None, None

    _, ext = os.path.splitext(image.filename or "")
    ext = (ext or ".png").lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ImageValidationError(f"Unsupported image extension: {ext or '(none)'}")

    img_bytes = await _read_bounded(image, MAX_IMAGE_BYTES)
    if not _matches_signature(ext, img_bytes):
        raise ImageValidationError("Image content does not match its extension")

    mime_type = image.content_type or DEFAULT_MIME_BY_EXTENSION.get(ext, "image/png")
    b64 = base64.b64encode(img_bytes).decode("ascii")
    return img_bytes, ext, b64, mime_type
