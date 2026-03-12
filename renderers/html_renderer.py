from typing import Dict, Any, Optional, List
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
p  { margin: 0 0 12px; text-align: justify; }
ul { margin: 0 0 12px 20px; }
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
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 20px auto;
}
"""

ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/svg+xml",
    "image/webp",
    "image/gif",
}


def _safe_image_mime_type(img_mime: Optional[str]) -> str:
    if img_mime in ALLOWED_IMAGE_MIME_TYPES:
        return img_mime
    return "image/png"


def render_flat_dict(data: Dict[str, Any]) -> str:
    """Fallback rendering if no structured schema is provided."""
    blocks: List[str] = []
    for k, v in data.items():
        k = str(k)
        if k == "h1":
            blocks.append(f"<h1>{esc(v)}</h1>")
        elif k.startswith("h2"):
            lbl = k.split(":", 1)[-1] if ":" in k else str(v)
            blocks.append(f"<h2>{esc(lbl)}</h2>")
        elif k.startswith("p:") or k == "p":
            blocks.append(f"<p>{esc(v)}</p>")
        elif k.startswith("list:") and isinstance(v, list):
            items = "".join(f"<li>{esc(it)}</li>" for it in v)
            blocks.append(f"<ul>{items}</ul>")
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

def render_structured(sections: List[Dict[str, Any]]) -> str:
    out: List[str] = []
    for s in sections:
        heading = s.get("heading")
        typ = s.get("type")
        if heading:
            out.append(f"<h2>{esc(heading)}</h2>")

        if typ == "paragraph":
            out.append(f"<p>{esc(s.get('text',''))}</p>")

        elif typ == "list":
            items = s.get("items") or []
            out.append("<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>")

        elif typ == "table":
            headers = s.get("headers") or []
            rows = s.get("rows") or []
            thead = ""
            if headers:
                thead = "<thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead>"
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
    data: Dict[str, Any],
    title: str,
    img_b64: Optional[str],
    img_mime: Optional[str],
) -> str:
    """Main entrypoint: wrap title, optional image, and data into full HTML."""
    body_blocks = [f"<h1>{esc(title)}</h1>"]

    if img_b64:
        mime_type = _safe_image_mime_type(img_mime)
        body_blocks.append(f'<img alt="image" src="data:{mime_type};base64,{img_b64}"/>')

    if isinstance(data, dict) and "sections" in data and isinstance(data["sections"], list):
        body_blocks.append(render_structured(data["sections"]))
    else:
        body_blocks.append(render_flat_dict(data))

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body>"
        + "\n".join(body_blocks)
        + "</body></html>"
    )
