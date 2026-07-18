from typing import Any

from schemas import DocumentStyle
from utils.sanitize import esc

CSS = """
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    max-width: 900px;
    margin: 24px auto;
    font-size: 12pt;
}
h1 { margin: 0 0 16px; font-size: 20pt; }
h2 { margin: 20px 0 10px; font-size: 14pt; }
h3 { margin: 16px 0 8px; font-size: 13pt; }
h4 { margin: 14px 0 6px; font-size: 12pt; font-weight: bold; }
h5 { margin: 12px 0 6px; font-size: 11pt; font-weight: bold; }
h6 { margin: 12px 0 6px; font-size: 10pt; font-weight: bold; font-style: italic; }
p  { margin: 0 0 12px; text-align: justify; }
ul, ol { margin: 0 0 12px 20px; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
}
td, th {
    border: 1px solid #ddd;
    padding: 6px 8px;
    vertical-align: top;
}
img.img-top, img.img-bottom {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 20px auto;
}
img.img-left {
    float: left;
    width: 40%;
    height: auto;
    margin: 0 16px 16px 0;
}
img.img-right {
    float: right;
    width: 40%;
    height: auto;
    margin: 0 0 16px 16px;
}
"""

ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/svg+xml",
    "image/webp",
    "image/gif",
}


def _safe_image_mime_type(img_mime: str | None) -> str:
    if img_mime in ALLOWED_IMAGE_MIME_TYPES:
        return img_mime
    return "image/png"


def _resolve_indent(section: dict[str, Any], default_indentation: float) -> float:
    indent = section.get("indentation")
    return default_indentation if indent is None else indent


def _indent_attr(indent: float) -> str:
    return f' style="margin-left:{indent}mm"' if indent else ""


def render_flat_dict(data: dict[str, Any], default_indentation: float = 0) -> str:
    """Fallback rendering if no structured schema is provided."""
    indent_attr = _indent_attr(default_indentation)
    blocks: list[str] = []
    for k, v in data.items():
        k = str(k)
        if k == "h1":
            blocks.append(f"<h1>{esc(v)}</h1>")
        elif k.startswith("h2"):
            lbl = k.split(":", 1)[-1] if ":" in k else str(v)
            blocks.append(f"<h2>{esc(lbl)}</h2>")
        elif k.startswith("p:") or k == "p":
            blocks.append(f"<p{indent_attr}>{esc(v)}</p>")
        elif k.startswith("list:") and isinstance(v, list):
            items = "".join(f"<li>{esc(it)}</li>" for it in v)
            blocks.append(f"<ul{indent_attr}>{items}</ul>")
        elif k.startswith("table:") and isinstance(v, dict):
            rows = "".join(
                f"<tr><td><strong>{esc(kk)}</strong></td><td>{esc(vv)}</td></tr>"
                for kk, vv in v.items()
            )
            blocks.append(f"<table>{rows}</table>")
        else:
            # generic key/value fallback
            blocks.append(f"<p><strong>{esc(k)}:</strong> {esc(v)}</p>")
    return "\n".join(blocks)

def render_structured(sections: list[dict[str, Any]], default_indentation: float = 0) -> str:
    out: list[str] = []
    for s in sections:
        heading = s.get("heading")
        typ = s.get("type")
        if heading:
            level = s.get("heading_level") or 2
            out.append(f"<h{level}>{esc(heading)}</h{level}>")

        if typ == "paragraph":
            indent_attr = _indent_attr(_resolve_indent(s, default_indentation))
            out.append(f"<p{indent_attr}>{esc(s.get('text',''))}</p>")

        elif typ == "list":
            indent_attr = _indent_attr(_resolve_indent(s, default_indentation))
            items = s.get("items") or []
            list_items = "".join(f"<li>{esc(i)}</li>" for i in items)
            tag = "ol" if s.get("ordered") else "ul"
            out.append(f"<{tag}{indent_attr}>{list_items}</{tag}>")

        elif typ == "table":
            headers = s.get("headers") or []
            rows = s.get("rows") or []
            thead = ""
            if headers:
                header_cells = "".join(f"<th>{esc(h)}</th>" for h in headers)
                thead = f"<thead><tr>{header_cells}</tr></thead>"
            body_rows = []
            for row in rows:
                body_rows.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
            out.append(f"<table>{thead}<tbody>{''.join(body_rows)}</tbody></table>")

        elif typ == "kv":
            items = s.get("items") or {}
            kv_rows = "".join(
                f"<tr><td><strong>{esc(k)}</strong></td><td>{esc(v)}</td></tr>"
                for k, v in items.items()
            )
            out.append(f"<table><tbody>{kv_rows}</tbody></table>")
    return "\n".join(out)


def json_to_html(
    data: dict[str, Any],
    title: str,
    img_b64: str | None,
    img_mime: str | None,
    style: DocumentStyle,
) -> str:
    """Main entrypoint: wrap title, optional image, and data into full HTML."""
    body_blocks = [f"<h1>{esc(title)}</h1>"]

    image_html = ""
    if img_b64:
        mime_type = _safe_image_mime_type(img_mime)
        image_html = (
            f'<img alt="image" class="img-{style.image_position}" '
            f'src="data:{mime_type};base64,{img_b64}"/>'
        )

    if image_html and style.image_position != "bottom":
        body_blocks.append(image_html)

    if isinstance(data, dict) and "sections" in data and isinstance(data["sections"], list):
        body_blocks.append(
            render_structured(data["sections"], default_indentation=style.indentation)
        )
    else:
        body_blocks.append(render_flat_dict(data, default_indentation=style.indentation))

    if image_html and style.image_position == "bottom":
        body_blocks.append('<div style="clear:both"></div>')
        body_blocks.append(image_html)

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body>"
        + "\n".join(body_blocks)
        + "</body></html>"
    )
