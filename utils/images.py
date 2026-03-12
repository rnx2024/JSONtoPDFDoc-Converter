import base64
import os
import tempfile
from typing import Optional, Tuple

from fastapi import UploadFile

DEFAULT_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


def save_temp_upload(
    image: Optional[UploadFile],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not image:
        return None, None, None, None

    b = image.file.read()
    _, ext = os.path.splitext(image.filename or "")
    ext = (ext or ".png").lower()
    mime_type = image.content_type or DEFAULT_MIME_BY_EXTENSION.get(ext, "image/png")

    tf = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tf.write(b)
    tf.close()

    b64 = base64.b64encode(b).decode("ascii")
    return tf.name, ext, b64, mime_type
