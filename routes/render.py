import contextlib
import logging
import os

from fastapi import APIRouter, File, Form, Request, UploadFile
from starlette.responses import JSONResponse, Response

from config import limiter
from services.render_service import (
    ServiceError,
    build_html,
    normalize_output,
    parse_json_bytes,
    parse_json_text,
    render_docx_output_bytes,
    render_pdf_bytes,
    validate_image_for_output,
)
from utils.images import ImageValidationError, save_temp_upload

logger = logging.getLogger(__name__)

router = APIRouter()


def _error_response(
    error: str,
    status_code: int,
    request_id: str | None,
    detail: object = None,
) -> JSONResponse:
    # detail may echo back user-supplied content (e.g. JSON parse error context);
    # keep it out of the server log, only the error code/status are logged.
    logger.error("render failed request_id=%s error=%s status=%s", request_id, error, status_code)
    body = {"error": error}
    if request_id is not None:
        body["request_id"] = request_id
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(body, status_code=status_code)


@router.get("/health")
async def health() -> dict:
    return {"ok": True}

@router.post("/render")
@limiter.limit("10/minute")
async def render(
    # Accept EITHER JSON text OR JSON file
    request: Request,
    json_text: str | None = Form(None),
    text: UploadFile | None = File(None),
    output: str = Form(...),
    title: str = Form("Document"),
    image: UploadFile | None = File(None),
) -> Response:
    request_id = request.headers.get("x-request-id")

    if text is not None and json_text is not None:
        return _error_response(
            error="MULTIPLE_JSON_INPUTS",
            status_code=400,
            request_id=request_id,
        )

    try:
        normalized_output = normalize_output(output)

        if text is not None:
            payload_bytes = await text.read()
            data = parse_json_bytes(payload_bytes)
        elif json_text is not None:
            data = parse_json_text(json_text)
        else:
            return _error_response(
                error="MISSING_JSON",
                status_code=400,
                request_id=request_id,
            )
    except ServiceError as exc:
        return _error_response(
            error=exc.code,
            status_code=exc.status_code,
            request_id=request_id,
            detail=exc.detail,
        )

    # Save image if provided
    try:
        img_path, img_ext, img_b64, img_mime = save_temp_upload(image)
    except ImageValidationError as exc:
        return _error_response(
            error="INVALID_IMAGE",
            status_code=400,
            request_id=request_id,
            detail=str(exc),
        )
    except OSError as exc:
        return _error_response(
            error="IMAGE_UPLOAD_SAVE_FAILED",
            status_code=500,
            request_id=request_id,
            detail=str(exc),
        )

    try:
        validate_image_for_output(normalized_output, img_ext)

        safe_title = title.strip() or "Document"

        if normalized_output == "docx":
            docx_bytes = render_docx_output_bytes(data, safe_title, img_path)
            logger.info("render succeeded request_id=%s output=docx", request_id)
            return Response(
                docx_bytes,
                200,
                headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'},
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        html = build_html(data, title=safe_title, img_b64=img_b64, img_mime=img_mime)
        pdf_bytes = render_pdf_bytes(html)
        logger.info("render succeeded request_id=%s output=pdf", request_id)
        return Response(
            pdf_bytes,
            200,
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'},
            media_type="application/pdf",
        )
    except ServiceError as exc:
        return _error_response(
            error=exc.code,
            status_code=exc.status_code,
            request_id=request_id,
            detail=exc.detail,
        )
    finally:
        # Temp file cleanup failure should not hide the response.
        if img_path and os.path.exists(img_path):
            with contextlib.suppress(OSError):
                os.unlink(img_path)
