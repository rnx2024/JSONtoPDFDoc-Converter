# ---- builder ----
FROM debian:bookworm-slim AS builder

# pin uv tool image version when copying the binary
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

# base tools only for build
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy only files needed to resolve deps first (better cache)
COPY pyproject.toml uv.lock ./
# install Python runtime used by uv
# if you keep a .python-version file, uncomment the two lines below and delete the fixed version:
# RUN uv python install "$(cat .python-version)"
# otherwise, explicitly pick a version:
RUN uv python install 3.12.4

# sync deps into a local .venv (project will be copied next)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# now copy app source
COPY . .

# install project into .venv (if you use PEP 517/editable, keep as is)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime ----
FROM debian:bookworm-slim

# create non-root user
RUN useradd -m -r -s /usr/sbin/nologin app

# install wkhtmltopdf and fonts (runtime only)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      wkhtmltopdf \
      fonts-dejavu \
      xfonts-base \
    && rm -rf /var/lib/apt/lists/*

# copy Python runtime and app from builder
COPY --from=builder --chown=app:app /python /python
COPY --from=builder --chown=app:app /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}"
USER app

EXPOSE 8000

# app exposes GET /health
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD \
  curl -fsS http://127.0.0.1:8000/health || exit 1

# prefer uvicorn over the fastapi CLI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
