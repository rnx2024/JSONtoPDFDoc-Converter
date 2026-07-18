import json

import pytest

from services.render_service import (
    MAX_JSON_BYTES,
    ServiceError,
    extract_style,
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


@pytest.mark.parametrize("heading_level", [1, 7])
def test_parse_json_text_rejects_out_of_range_heading_level(heading_level):
    section = {
        "heading": "H",
        "type": "paragraph",
        "text": "x",
        "heading_level": heading_level,
    }
    payload = json.dumps({"sections": [section]})
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text(payload)
    assert exc_info.value.code == "INVALID_STRUCTURED_DOC"


def test_parse_json_text_accepts_in_range_heading_level():
    payload = json.dumps(
        {"sections": [{"heading": "H", "type": "paragraph", "text": "x", "heading_level": 3}]}
    )
    data = parse_json_text(payload)
    assert data["sections"][0]["heading_level"] == 3


@pytest.mark.parametrize("ordered", [True, False])
def test_parse_json_text_accepts_ordered_bool(ordered):
    payload = json.dumps({"sections": [{"type": "list", "items": ["a"], "ordered": ordered}]})
    data = parse_json_text(payload)
    assert data["sections"][0]["ordered"] == ordered


def test_parse_json_text_rejects_non_bool_ordered():
    payload = json.dumps({"sections": [{"type": "list", "items": ["a"], "ordered": "maybe"}]})
    with pytest.raises(ServiceError) as exc_info:
        parse_json_text(payload)
    assert exc_info.value.code == "INVALID_STRUCTURED_DOC"


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


def test_extract_style_defaults_when_absent():
    style = extract_style({"title": "t"})
    assert style.image_position == "top"
    assert style.indentation == 0
    assert (style.margin.top, style.margin.right, style.margin.bottom, style.margin.left) == (
        12,
        12,
        16,
        12,
    )


def test_extract_style_custom_values():
    style = extract_style(
        {
            "style": {
                "margin": {"top": 5, "right": 5, "bottom": 5, "left": 5},
                "indentation": 8,
                "image_position": "left",
            }
        }
    )
    assert style.image_position == "left"
    assert style.indentation == 8
    assert style.margin.top == 5


def test_extract_style_invalid_image_position():
    with pytest.raises(ServiceError) as exc_info:
        extract_style({"style": {"image_position": "diagonal"}})
    assert exc_info.value.code == "INVALID_STYLE"
    assert exc_info.value.status_code == 400


def test_extract_style_rejects_unknown_field():
    with pytest.raises(ServiceError) as exc_info:
        extract_style({"style": {"bogus": 1}})
    assert exc_info.value.code == "INVALID_STYLE"
