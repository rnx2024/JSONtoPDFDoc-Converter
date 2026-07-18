from renderers.html_renderer import json_to_html
from schemas import DocumentStyle

DATA = {"sections": [{"type": "paragraph", "text": "hello"}]}
IMG_B64 = "aGVsbG8="  # arbitrary base64, content doesn't matter for HTML assembly


def test_default_style_places_image_top_before_sections():
    html = json_to_html(
        DATA, title="T", img_b64=IMG_B64, img_mime="image/png", style=DocumentStyle()
    )
    img_index = html.index('class="img-top"')
    section_index = html.index("hello")
    assert img_index < section_index


def test_bottom_position_places_image_after_sections():
    style = DocumentStyle(image_position="bottom")
    html = json_to_html(DATA, title="T", img_b64=IMG_B64, img_mime="image/png", style=style)
    img_index = html.index('class="img-bottom"')
    section_index = html.index("hello")
    assert section_index < img_index


def test_left_and_right_positions_use_matching_css_class():
    for position in ("left", "right"):
        style = DocumentStyle(image_position=position)
        html = json_to_html(DATA, title="T", img_b64=IMG_B64, img_mime="image/png", style=style)
        assert f'class="img-{position}"' in html


def test_no_image_omits_img_tag():
    html = json_to_html(DATA, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "<img" not in html


def test_default_indentation_emits_no_style_attribute():
    html = json_to_html(DATA, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "margin-left" not in html


def test_document_default_indentation_applied_to_paragraph():
    style = DocumentStyle(indentation=10)
    html = json_to_html(DATA, title="T", img_b64=None, img_mime=None, style=style)
    assert 'style="margin-left:10.0mm"' in html


def test_section_indentation_overrides_document_default():
    data = {"sections": [{"type": "paragraph", "text": "hi", "indentation": 25}]}
    style = DocumentStyle(indentation=10)
    html = json_to_html(data, title="T", img_b64=None, img_mime=None, style=style)
    assert 'style="margin-left:25mm"' in html
    assert 'style="margin-left:10mm"' not in html


def test_default_heading_level_is_h2():
    data = {"sections": [{"heading": "H", "type": "paragraph", "text": "x"}]}
    html = json_to_html(data, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "<h2>H</h2>" in html


def test_custom_heading_level():
    data = {"sections": [{"heading": "H", "type": "paragraph", "text": "x", "heading_level": 4}]}
    html = json_to_html(data, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "<h4>H</h4>" in html
    assert "<h2>H</h2>" not in html


def test_default_list_is_unordered():
    data = {"sections": [{"type": "list", "items": ["a", "b"]}]}
    html = json_to_html(data, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "<ul>" in html
    assert "<ol>" not in html


def test_ordered_list_renders_ol():
    data = {"sections": [{"type": "list", "items": ["a", "b"], "ordered": True}]}
    html = json_to_html(data, title="T", img_b64=None, img_mime=None, style=DocumentStyle())
    assert "<ol>" in html
    assert "</ol>" in html
    assert "<ul>" not in html
