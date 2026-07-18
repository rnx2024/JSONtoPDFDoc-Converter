import json

import pytest

from services.render_service import (
    MAX_JSON_BYTES,
    ServiceError,
    normalize_output,
    parse_json_bytes,
    parse_json_text,
    validate_image_for_output,
)


def test_parse_json_text_valid():
    assert parse_json_text('{"title": "t"}') == {"title": "t"}


def test_parse_json_text_invalid_json():
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text("{not json")
    assert exc_info.value.code == "INVALID_JSON"
    assert exc_info.value.status_code == 400


def test_parse_json_text_non_dict_root():
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text("[1, 2, 3]")
    assert exc_info.value.code == "JSON_ROOT_NOT_OBJECT"


def test_parse_json_text_too_large():
    huge = json.dumps({"title": "x" * (MAX_JSON_BYTES + 1)})
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text(huge)
    assert exc_info.value.code == "JSON_TOO_LARGE"
    assert exc_info.value.status_code == 413


def test_parse_json_text_valid_structured_doc():
    payload = json.dumps(
        {
            "title": "Report",
            "sections": [{"heading": "H", "type": "paragraph", "text": "body"}],
        }
    )
    data = parse_json_text(payload)
    assert data["sections"][0]["type"] == "paragraph"


def test_parse_json_text_invalid_structured_doc_missing_type():
    payload = json.dumps({"sections": [{"heading": "H"}]})
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text(payload)
    assert exc_info.value.code == "INVALID_STRUCTURED_DOC"


def test_parse_json_text_rejects_unknown_section_field():
    payload = json.dumps({"sections": [{"type": "paragraph", "text": "x", "bogus": 1}]})
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text(payload)
    assert exc_info.value.code == "INVALID_STRUCTURED_DOC"


def test_parse_json_text_allows_table_headers_field():
    # regression check: "headers" must stay a recognized Section field (see assets/payload.json)
    payload = json.dumps(
        {
            "sections": [
                {"type": "table", "headers": ["A", "B"], "rows": [["1", "2"]]},
            ]
        }
    )
    data = parse_json_text(payload)
    assert data["sections"][0]["headers"] == ["A", "B"]


def test_parse_json_bytes_valid():
    assert parse_json_bytes(b'{"title": "t"}') == {"title": "t"}


def test_parse_json_bytes_bad_encoding():
    with pytest.raises(ServiceError) as exc_info:
        parse_json_bytes(b"\xff\xfe\x00")
    assert exc_info.value.code == "INVALID_JSON_ENCODING"


def test_parse_json_bytes_too_large():
    with pytest.raises(ServiceError) as exc_info:
        parse_json_bytes(b"x" * (MAX_JSON_BYTES + 1))
    assert exc_info.value.code == "JSON_TOO_LARGE"


@pytest.mark.parametrize("raw,expected", [("pdf", "pdf"), (" PDF ", "pdf"), ("DOCX", "docx")])
def test_normalize_output_valid(raw, expected):
    assert normalize_output(raw) == expected


def test_normalize_output_invalid():
    with pytest.raises(ServiceError) as exc_info:
        normalize_output("txt")
    assert exc_info.value.code == "INVALID_OUTPUT"


def test_validate_image_for_output_svg_docx_rejected():
    with pytest.raises(ServiceError) as exc_info:
        validate_image_for_output("docx", ".svg")
    assert exc_info.value.code == "SVG_NOT_SUPPORTED_FOR_DOCX"


def test_validate_image_for_output_svg_pdf_allowed():
    validate_image_for_output("pdf", ".svg")


def test_validate_image_for_output_no_image():
    validate_image_for_output("docx", None)
