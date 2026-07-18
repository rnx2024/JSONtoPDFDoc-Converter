import base64
import os
import tempfile

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


def _read_bounded(image: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = image.file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ImageValidationError(f"Image exceeds maximum size of {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def save_temp_upload(
    image: UploadFile | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not image:
        return None, None, None, None

    _, ext = os.path.splitext(image.filename or "")
    ext = (ext or ".png").lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ImageValidationError(f"Unsupported image extension: {ext or '(none)'}")

    b = _read_bounded(image, MAX_IMAGE_BYTES)
    if not _matches_signature(ext, b):
        raise ImageValidationError("Image content does not match its extension")

    mime_type = image.content_type or DEFAULT_MIME_BY_EXTENSION.get(ext, "image/png")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
        tf.write(b)
        tf_name = tf.name

    b64 = base64.b64encode(b).decode("ascii")
    return tf_name, ext, b64, mime_type
