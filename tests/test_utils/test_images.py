import io

import pytest

from utils.images import MAX_IMAGE_BYTES, ImageValidationError, validate_and_read_image

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class FakeUploadFile:
    def __init__(self, filename, content, content_type=None):
        self.filename = filename
        self.content_type = content_type
        self._buf = io.BytesIO(content)

    async def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)


async def test_validate_and_read_image_none_returns_all_none():
    assert await validate_and_read_image(None) == (None, None, None, None)


async def test_validate_and_read_image_valid_png():
    content = PNG_SIGNATURE + b"fakepngdata"
    upload = FakeUploadFile("photo.png", content)
    img_bytes, ext, b64, mime = await validate_and_read_image(upload)
    assert ext == ".png"
    assert mime == "image/png"
    assert b64
    assert img_bytes == content


async def test_validate_and_read_image_rejects_disallowed_extension():
    upload = FakeUploadFile("payload.exe", b"MZfakecontent")
    with pytest.raises(ImageValidationError):
        await validate_and_read_image(upload)


async def test_validate_and_read_image_rejects_mismatched_signature():
    upload = FakeUploadFile("fake.png", b"not-a-real-png-file")
    with pytest.raises(ImageValidationError):
        await validate_and_read_image(upload)


async def test_validate_and_read_image_rejects_oversized_file():
    content = PNG_SIGNATURE + b"0" * (MAX_IMAGE_BYTES + 1)
    upload = FakeUploadFile("big.png", content)
    with pytest.raises(ImageValidationError):
        await validate_and_read_image(upload)
