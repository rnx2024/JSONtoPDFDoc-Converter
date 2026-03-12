import json
from json import JSONDecodeError
from typing import Any, Optional

from pydantic import ValidationError

from renderers.html_renderer import json_to_html
from renderers.pdf_renderer import html_to_pdf_bytes
from renderers.docx_renderer import render_docx_bytes
from schemas import StructuredDoc

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


def parse_json_text(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
    except JSONDecodeError as exc:
        raise ServiceError("INVALID_JSON", detail=str(exc), status_code=400) from exc

    if not isinstance(data, dict):
        raise ServiceError("JSON_ROOT_NOT_OBJECT", status_code=400)

    _validate_structured_doc_if_present(data)
    return data


def parse_json_bytes(payload_bytes: bytes) -> dict[str, Any]:
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


def validate_image_for_output(output: str, image_extension: Optional[str]) -> None:
    if output == "docx" and image_extension == ".svg":
        raise ServiceError("SVG_NOT_SUPPORTED_FOR_DOCX", status_code=400)


def build_html(
    data: dict[str, Any],
    title: str,
    img_b64: Optional[str],
    img_mime: Optional[str],
) -> str:
    return json_to_html(data, title=title, img_b64=img_b64, img_mime=img_mime)


def render_pdf_bytes(html: str) -> bytes:
    try:
        return html_to_pdf_bytes(html)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ServiceError("PDF_RENDER_FAILED", detail=str(exc), status_code=500) from exc


def render_docx_output_bytes(data: dict[str, Any], title: str, img_path: Optional[str]) -> bytes:
    try:
        return render_docx_bytes(data, title=title, img_path=img_path)
    except (FileNotFoundError, TypeError, ValueError) as exc:
        raise ServiceError("DOCX_RENDER_FAILED", detail=str(exc), status_code=500) from exc
