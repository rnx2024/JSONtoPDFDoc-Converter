import io
from typing import Dict, Any, Optional
from docx import Document
from docx.image.exceptions import UnrecognizedImageError
from docx.shared import Inches

def render_docx_bytes(data: Dict[str, Any], title: str, img_path: Optional[str]) -> bytes:
    doc = Document()
    doc.add_heading(title, level=1)

    if img_path:
        try:
            doc.add_picture(img_path, width=Inches(6.0))
        except (FileNotFoundError, UnrecognizedImageError, ValueError):
            pass

    if isinstance(data, dict) and "sections" in data and isinstance(data["sections"], list):
        for s in data["sections"]:
            heading = s.get("heading")
            typ = s.get("type")
            if heading:
                doc.add_heading(str(heading), level=2)
            if typ == "paragraph":
                doc.add_paragraph(str(s.get("text", "")))
            elif typ == "list":
                for it in (s.get("items") or []):
                    doc.add_paragraph(str(it), style="List Bullet")
            elif typ == "table":
                rows = s.get("rows") or []
                if rows:
                    cols = max(len(r) for r in rows)
                    t = doc.add_table(rows=0, cols=cols)
                    for r in rows:
                        cells = t.add_row().cells
                        for i, val in enumerate(r):
                            cells[i].text = str(val)
    else:
        t = doc.add_table(rows=1, cols=2)
        hdr = t.rows[0].cells
        hdr[0].text = "Key"; hdr[1].text = "Value"
        for k, v in (data or {}).items():
            if isinstance(v, dict):
                sub = doc.add_table(rows=1, cols=2)
                h = sub.rows[0].cells
                h[0].text = str(k); h[1].text = ""
                for kk, vv in v.items():
                    r = sub.add_row().cells
                    r[0].text = str(kk); r[1].text = str(vv)
            else:
                r = t.add_row().cells
                r[0].text = str(k); r[1].text = str(v)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
