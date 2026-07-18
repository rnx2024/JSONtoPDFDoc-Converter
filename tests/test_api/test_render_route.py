import pytest

from config import limiter

VALID_JSON = '{"title": "Report", "sections": [{"type": "paragraph", "text": "hi"}]}'
AUTH_HEADERS = {"x-api-key": "test-api-key"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


async def test_health(client):
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_render_requires_api_key(client):
    resp = await client.post("/v1/render", data={"json_text": VALID_JSON, "output": "docx"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "INVALID_API_KEY"


async def test_render_rejects_wrong_api_key(client):
    resp = await client.post(
        "/v1/render",
        data={"json_text": VALID_JSON, "output": "docx"},
        headers={"x-api-key": "wrong-key"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "INVALID_API_KEY"


async def test_render_returns_503_when_api_key_not_configured(client, monkeypatch):
    import auth

    monkeypatch.setattr(auth, "API_KEY", None)
    resp = await client.post(
        "/v1/render", data={"json_text": VALID_JSON, "output": "docx"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 503
    assert resp.json()["error"] == "API_KEY_NOT_CONFIGURED"


async def test_render_docx_success(client):
    resp = await client.post(
        "/v1/render", data={"json_text": VALID_JSON, "output": "docx"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


async def test_render_pdf_success(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.HTML.write_pdf", lambda self, *a, **k: b"%PDF-fake")
    resp = await client.post(
        "/v1/render", data={"json_text": VALID_JSON, "output": "pdf"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-fake"


async def test_render_missing_json(client):
    resp = await client.post("/v1/render", data={"output": "docx"}, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    assert resp.json()["error"] == "MISSING_JSON"


async def test_render_both_json_inputs_given(client):
    resp = await client.post(
        "/v1/render",
        data={"json_text": VALID_JSON, "output": "docx"},
        files={"text": ("data.json", VALID_JSON, "application/json")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "MULTIPLE_JSON_INPUTS"


async def test_render_invalid_output(client):
    resp = await client.post(
        "/v1/render", data={"json_text": VALID_JSON, "output": "txt"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_OUTPUT"


async def test_render_invalid_json(client):
    resp = await client.post(
        "/v1/render", data={"json_text": "{not json", "output": "docx"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_JSON"


async def test_render_rejects_invalid_image(client):
    resp = await client.post(
        "/v1/render",
        data={"json_text": VALID_JSON, "output": "docx"},
        files={"image": ("payload.exe", b"MZfakecontent", "application/octet-stream")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_IMAGE"


async def test_render_rate_limit_returns_429_after_ten_requests(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.HTML.write_pdf", lambda self, *a, **k: b"%PDF-fake")
    for _ in range(10):
        resp = await client.post(
            "/v1/render", data={"json_text": VALID_JSON, "output": "pdf"}, headers=AUTH_HEADERS
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/v1/render", data={"json_text": VALID_JSON, "output": "pdf"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 429


STYLED_JSON = (
    '{"title": "Report", "sections": [{"type": "paragraph", "text": "hi", "indentation": 5}],'
    ' "style": {"margin": {"top": 5, "right": 5, "bottom": 5, "left": 5},'
    ' "indentation": 2, "image_position": "left"}}'
)


async def test_render_with_style_block_docx_success(client):
    resp = await client.post(
        "/v1/render", data={"json_text": STYLED_JSON, "output": "docx"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 200


async def test_render_with_style_block_pdf_success(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.HTML.write_pdf", lambda self, *a, **k: b"%PDF-fake")
    resp = await client.post(
        "/v1/render", data={"json_text": STYLED_JSON, "output": "pdf"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 200


async def test_render_invalid_style_rejected(client):
    invalid_json = '{"title": "t", "style": {"image_position": "diagonal"}}'
    resp = await client.post(
        "/v1/render", data={"json_text": invalid_json, "output": "docx"}, headers=AUTH_HEADERS
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_STYLE"


CONTENT_STYLED_JSON = (
    '{"title": "Report", "sections": ['
    '{"heading": "H", "type": "paragraph", "text": "hi", "heading_level": 3},'
    '{"type": "list", "items": ["a", "b"], "ordered": true}'
    "]}"
)


async def test_render_with_heading_level_and_ordered_list_docx_success(client):
    resp = await client.post(
        "/v1/render",
        data={"json_text": CONTENT_STYLED_JSON, "output": "docx"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200


async def test_render_with_heading_level_and_ordered_list_pdf_success(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.HTML.write_pdf", lambda self, *a, **k: b"%PDF-fake")
    resp = await client.post(
        "/v1/render",
        data={"json_text": CONTENT_STYLED_JSON, "output": "pdf"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
