import pytest

from config import limiter

VALID_JSON = '{"title": "Report", "sections": [{"type": "paragraph", "text": "hi"}]}'


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_render_docx_success(client):
    resp = await client.post("/render", data={"json_text": VALID_JSON, "output": "docx"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


async def test_render_pdf_success(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.pdfkit.from_string", lambda *a, **k: b"%PDF-fake")
    resp = await client.post("/render", data={"json_text": VALID_JSON, "output": "pdf"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-fake"


async def test_render_missing_json(client):
    resp = await client.post("/render", data={"output": "docx"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "MISSING_JSON"


async def test_render_both_json_inputs_given(client):
    resp = await client.post(
        "/render",
        data={"json_text": VALID_JSON, "output": "docx"},
        files={"text": ("data.json", VALID_JSON, "application/json")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "MULTIPLE_JSON_INPUTS"


async def test_render_invalid_output(client):
    resp = await client.post("/render", data={"json_text": VALID_JSON, "output": "txt"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_OUTPUT"


async def test_render_invalid_json(client):
    resp = await client.post("/render", data={"json_text": "{not json", "output": "docx"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_JSON"


async def test_render_rejects_invalid_image(client):
    resp = await client.post(
        "/render",
        data={"json_text": VALID_JSON, "output": "docx"},
        files={"image": ("payload.exe", b"MZfakecontent", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_IMAGE"


async def test_render_rate_limit_returns_429_after_ten_requests(client, monkeypatch):
    monkeypatch.setattr("renderers.pdf_renderer.pdfkit.from_string", lambda *a, **k: b"%PDF-fake")
    for _ in range(10):
        resp = await client.post("/render", data={"json_text": VALID_JSON, "output": "pdf"})
        assert resp.status_code == 200

    resp = await client.post("/render", data={"json_text": VALID_JSON, "output": "pdf"})
    assert resp.status_code == 429
