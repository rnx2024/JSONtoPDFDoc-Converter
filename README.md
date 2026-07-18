# JSON → PDF / DOCX Converter API

A FastAPI service that accepts JSON data (and optional images) and generates professional PDF or DOCX reports.  
Internally, the service transforms JSON into styled HTML, then renders it with **WeasyPrint** (for PDFs) or **python-docx** (for DOCX).

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

**2. Install WeasyPrint's native dependencies**

WeasyPrint needs Pango (a text-layout library) installed at the OS level — `pip`/`uv` alone can't provide this.

- **Docker**: nothing to do — the `Dockerfile` installs the required `libpango`/`libharfbuzz` packages already.
- **Linux**: `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` (Debian/Ubuntu) or your distro's equivalent.
- **macOS**: `brew install pango`.
- **Windows**: native Windows needs [MSYS2](https://www.msys2.org/) — install it with default options, then from the MSYS2 shell run `pacman -S mingw-w64-x86_64-pango`. See [WeasyPrint's Windows install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows) if you hit DLL-loading errors — you may need to set `WEASYPRINT_DLL_DIRECTORIES` to point at the MSYS2 install path.

**3. Run app**
```
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://127.0.0.1:8000/docs
 for interactive API docs.

API Endpoints
GET /v1/health
POST /v1/render
 - Generate a report. Requires an `x-api-key` header matching the server's configured `API_KEY`.
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

- `main.py` — FastAPI app factory, router (mounted at `/v1`), rate-limiter registration, Redis startup check, Sentry init.
- `auth.py` — API-key verification dependency for protected routes.
- `config.py` — single source of truth for all environment configuration, via a `pydantic-settings` `Settings` class; also builds the shared rate-limiter instance and retry constants.
- `adapters/` — external service integrations; `adapters/redis.py` holds the Redis connectivity check (retryguard + tenacity) and its custom exception-classification rule.
- `schemas.py` — Pydantic models for the structured `sections` document format.
- `routes/` — thin route handlers (`/v1/health`, `/v1/render`); validates input, delegates, returns response.
- `services/` — business logic: JSON parsing/validation, output normalization, error mapping.
- `renderers/` — HTML/PDF/DOCX generation from parsed JSON.
- `utils/` — shared helpers: HTML escaping, image upload validation (in-memory, no temp files).

## Environment Variables

All environment variables are read in one place: `config.py`'s `Settings` class (backed by `pydantic-settings`, which also loads a local `.env` file automatically).

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | Yes | Shared secret clients must send as `x-api-key` to call `POST /v1/render`. If unset, that endpoint returns 503. |
| `REDIS_URL` | Yes | Redis connection string backing distributed rate limiting. The app fails to start if this isn't set — there's no in-memory fallback. |
| `LOG_LEVEL` | No | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Defaults to `INFO`. |
| `SENTRY_DSN` | No | Sentry error-tracking DSN. Sentry is fully inert (no-op) if this isn't set — local dev and CI never send data. |
| `ENV` | No | Environment name (`development`, `staging`, `production`) attached to Sentry events. Defaults to `development`. |

## Testing

```
uv sync --group dev
uv run pytest -v
uv run ruff check .
```

Tests cover JSON/output/image/style validation logic (`tests/test_services`, `tests/test_utils`), HTML/DOCX rendering behavior including margins, image position, and indentation (`tests/test_renderers`), and the `/v1/render` and `/v1/health` routes end-to-end (`tests/test_api`), including auth and the rate limiter. PDF rendering is tested with `weasyprint.HTML.write_pdf` mocked out — no native WeasyPrint libraries are required to run the suite, but a reachable Redis (`REDIS_URL`) is, since the app now fails to start without one. Locally, that's easiest via a throwaway container: `docker run --rm -p 6379:6379 redis:7-alpine`.

## Deployment

The included `Dockerfile` builds a non-root, multi-stage image with WeasyPrint's native dependencies installed, exposing port `8000` with a `/v1/health` healthcheck. `render.yaml` deploys that image to [Render](https://render.com) as a Docker web service.
