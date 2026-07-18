import io
import os

import pytest

from utils.images import MAX_IMAGE_BYTES, ImageValidationError, save_temp_upload

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class FakeUploadFile:
    def __init__(self, filename, content, content_type=None):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(content)


def test_save_temp_upload_none_returns_all_none():
    assert save_temp_upload(None) == (None, None, None, None)


def test_save_temp_upload_valid_png():
    content = PNG_SIGNATURE + b"fakepngdata"
    upload = FakeUploadFile("photo.png", content)
    path, ext, b64, mime = save_temp_upload(upload)
    try:
        assert ext == ".png"
        assert mime == "image/png"
        assert b64
        with open(path, "rb") as f:
            assert f.read() == content
    finally:
        os.unlink(path)


def test_save_temp_upload_rejects_disallowed_extension():
    upload = FakeUploadFile("payload.exe", b"MZfakecontent")
    with pytest.raises(ImageValidationError):
        save_temp_upload(upload)


def test_save_temp_upload_rejects_mismatched_signature():
    upload = FakeUploadFile("fake.png", b"not-a-real-png-file")
    with pytest.raises(ImageValidationError):
        save_temp_upload(upload)


def test_save_temp_upload_rejects_oversized_file():
    content = PNG_SIGNATURE + b"0" * (MAX_IMAGE_BYTES + 1)
    upload = FakeUploadFile("big.png", content)
    with pytest.raises(ImageValidationError):
        save_temp_upload(upload)
