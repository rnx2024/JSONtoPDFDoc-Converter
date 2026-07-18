import json
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from renderers.docx_renderer import render_docx_bytes
from renderers.html_renderer import json_to_html
from renderers.pdf_renderer import html_to_pdf_bytes
from schemas import DocumentStyle, Margin, StructuredDoc

MAX_JSON_BYTES = 2_000_000  # 2 MB


class ServiceError(Exception):
    def __init__(self, code: str, detail: Any = None, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def _validate_structured_doc_if_present(data: dict[str, Any]) -> None:
    if "sections" not in data:
        return

    try:
        StructuredDoc.model_validate(data)
    except ValidationError as exc:
        raise ServiceError(
            "INVALID_STRUCTURED_DOC",
            detail=exc.errors(include_url=False),
            status_code=400,
        ) from exc


def extract_style(data: dict[str, Any]) -> DocumentStyle:
    raw_style = data.get("style")
    if raw_style is None:
        return DocumentStyle()

    try:
        return DocumentStyle.model_validate(raw_style)
    except ValidationError as exc:
        raise ServiceError(
            "INVALID_STYLE",
            detail=exc.errors(include_url=False),
            status_code=400,
        ) from exc


def parse_json_text(json_text: str) -> dict[str, Any]:
    if len(json_text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ServiceError("JSON_TOO_LARGE", status_code=413)

    try:
        data = json.loads(json_text)
    except JSONDecodeError as exc:
        raise ServiceError("INVALID_JSON", detail=str(exc), status_code=400) from exc

    if not isinstance(data, dict):
        raise ServiceError("JSON_ROOT_NOT_OBJECT", status_code=400)

    _validate_structured_doc_if_present(data)
    return data


def parse_json_bytes(payload_bytes: bytes) -> dict[str, Any]:
    if len(payload_bytes) > MAX_JSON_BYTES:
        raise ServiceError("JSON_TOO_LARGE", status_code=413)

    try:
        json_text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ServiceError("INVALID_JSON_ENCODING", detail=str(exc), status_code=400) from exc

    return parse_json_text(json_text)


def normalize_output(output: str) -> str:
    normalized = output.strip().lower()
    if normalized not in {"pdf", "docx"}:
        raise ServiceError("INVALID_OUTPUT", status_code=400)
    return normalized


def validate_image_for_output(output: str, image_extension: str | None) -> None:
    if output == "docx" and image_extension == ".svg":
        raise ServiceError("SVG_NOT_SUPPORTED_FOR_DOCX", status_code=400)


def build_html(
    data: dict[str, Any],
    title: str,
    img_b64: str | None,
    img_mime: str | None,
    style: DocumentStyle,
) -> str:
    return json_to_html(data, title=title, img_b64=img_b64, img_mime=img_mime, style=style)


def render_pdf_bytes(html: str, margin: Margin) -> bytes:
    try:
        return html_to_pdf_bytes(html, margin=margin)
    except Exception as exc:
        # WeasyPrint doesn't document a narrow exception hierarchy for
        # rendering failures -- catch broadly at this third-party boundary so
        # any unexpected failure becomes a clean 500 instead of a raw traceback.
        raise ServiceError("PDF_RENDER_FAILED", detail=str(exc), status_code=500) from exc


def render_docx_output_bytes(
    data: dict[str, Any],
    title: str,
    img_bytes: bytes | None,
    style: DocumentStyle,
) -> bytes:
    try:
        return render_docx_bytes(data, title=title, img_bytes=img_bytes, style=style)
    except (TypeError, ValueError) as exc:
        raise ServiceError("DOCX_RENDER_FAILED", detail=str(exc), status_code=500) from exc
