# JSON → PDF / DOCX Converter API

A FastAPI service that accepts JSON data (and optional images) and generates professional PDF or DOCX reports.  
Internally, the service transforms JSON into styled HTML, then renders it with **wkhtmltopdf** (for PDFs) or **python-docx** (for DOCX).

---

## Features

- Accepts **JSON data** as inline text or uploaded file.  
- Embeds an optional image (PNG/JPEG recommended).  
- Outputs clean, paragraph-based reports instead of raw tables.  
- Two output formats: **PDF** or **DOCX**.  

---

## Installation

**1. Clone repo & install dependencies**
```
uv sync
```
Your pyproject.toml must include:
```
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pdfkit",
  "python-docx",
  "python-multipart",
  "python-dotenv"
]
```
**2. Install wkhtmltopdf system binary**
```
Windows: Download and install to
C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe

Add the bin folder to your PATH or set in .env:

WKHTMLTOPDF_PATH=C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe
```
**3. Run app**
```
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://127.0.0.1:8000/docs
 for interactive API docs.

API Endpoints
GET /health
POST /render
 - Generate a report.
 - Form-data fields:
```
json_text (string) — JSON content inline (alternative to file).
text (file) — JSON file upload.
image (file, optional) — PNG or JPEG to embed. (SVG works only in PDF, not DOCX).
output (string, required) — "pdf" or "docx".
title (string, optional) — Report title.
```
**Recommended schema for JSON format:**
```
{
  "title": "Quarterly Review",
  "sections": [
    {
      "heading": "Executive Summary",
      "type": "paragraph",
      "text": "This quarter we saw growth in all regions..."
    },
    {
      "heading": "KPIs",
      "type": "list",
      "items": ["Revenue +12%", "New hires: 10", "Customer churn -3%"]
    },
    {
      "heading": "Financials",
      "type": "table",
      "rows": [["Q1", "$1M"], ["Q2", "$1.2M"], ["Q3", "$1.3M"]]
    }
  ]
}
```
**Note:**
1. sections is an array of objects.
2. type can be:
   - "paragraph" → renders <p>…</p>
   - "list" → renders <ul><li>…</li></ul> (or <ol> if `"ordered": true`)
   - "table" → renders <table>…</table>
3. Any section with a `heading` can set `"heading_level": 2-6` (default 2 = `<h2>`/`Heading 2`).
4. A `list` section can set `"ordered": true` for a numbered list (`<ol>`/`List Number` style) instead of the default bulleted list (`<ul>`/`List Bullet` style).

**Flat dict fallback:**
If you send a simple JSON dict without sections, keys will be rendered as headings/paragraphs/tables depending on prefix (h1:, h2:, p:, list:, table:).

**Optional `style` block:**
All fields are optional and fall back to the defaults below if omitted or if `style` is missing entirely. Values are in millimeters.
```json
{
  "title": "Quarterly Review",
  "sections": [
    {"type": "paragraph", "text": "...", "indentation": 8}
  ],
  "style": {
    "margin": {"top": 12, "right": 12, "bottom": 16, "left": 12},
    "indentation": 0,
    "image_position": "top"
  }
}
```
- `margin` — page margins (PDF page / DOCX section margins). Document-level only.
- `indentation` — default left-indent applied to `paragraph`/`list` sections. Can be overridden per-section by setting `indentation` directly on that section (as shown above); not applied to `table`/`kv` sections.
- `image_position` — one of `top` (default), `bottom`, `left`, `right`. Document-level only (there's one image per request, not one per section). In the PDF output, `left`/`right` float the image with surrounding text wrapping around it (CSS). In DOCX, `left`/`right` only align the image — python-docx has no text-wrap capability, so there's no wrap in Word output.

**Image Guidelines**
```
Supported formats: PNG, JPEG, WEBP, GIF, SVG.
SVG: works in PDF but not in DOCX (raises error).
Images are scaled to page width (max-width:100%) and centered.
Extension and file content are both validated; unrecognized or
mismatched files are rejected. Max upload size: 5 MB.
```

---

## Project Structure

- `main.py` — FastAPI app factory, router and rate-limiter registration.
- `config.py` — shared config: wkhtmltopdf path/options, rate limiter instance.
- `schemas.py` — Pydantic models for the structured `sections` document format.
- `routes/` — thin route handlers (`/health`, `/render`); validates input, delegates, returns response.
- `services/` — business logic: JSON parsing/validation, output normalization, error mapping.
- `renderers/` — HTML/PDF/DOCX generation from parsed JSON.
- `utils/` — shared helpers: HTML escaping, image upload validation and temp-file handling.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `WKHTMLTOPDF_PATH` | No | Path to the `wkhtmltopdf` binary. Only needed if it's not on `PATH` (e.g. Windows local dev). Not needed in the Docker image, which installs it system-wide. |

## Testing

```
uv sync --group dev
uv run pytest -v
uv run ruff check .
```

Tests cover JSON/output/image/style validation logic (`tests/test_services`, `tests/test_utils`), HTML/DOCX rendering behavior including margins, image position, and indentation (`tests/test_renderers`), and the `/render` and `/health` routes end-to-end (`tests/test_api`), including the rate limiter. PDF rendering is tested with `pdfkit.from_string` mocked out — no `wkhtmltopdf` binary is required to run the suite.

## Deployment

The included `Dockerfile` builds a non-root, multi-stage image with `wkhtmltopdf` installed, exposing port `8000` with a `/health` healthcheck. `render.yaml` deploys that image to [Render](https://render.com) as a Docker web service.
