# Two stages: the Vite build of web/, then the Python image that serves it (D2).
# Base images are pinned by digest (multi-arch index); the tag is kept in a comment. To update:
# docker buildx imagetools inspect <tag> | grep -m1 Digest

# Web: Vue 3 + Vite build. The shell has no data; everything comes from the API.
# node:22-slim
FROM node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS web
WORKDIR /web
COPY web/package.json web/package-lock.json web/.npmrc ./
# No install scripts: dependencies run no code at install time.
RUN npm ci --ignore-scripts
COPY web ./
RUN npm run build

# API: FastAPI on uvicorn, serving /api and the web build with SPA fallback.
# python:3.12-slim
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
# ghcr.io/astral-sh/uv:0.13
COPY --from=ghcr.io/astral-sh/uv:0.13@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/alembic.ini ./
COPY backend/north ./north
RUN uv sync --frozen --no-dev
COPY --from=web /web/dist ./web/dist
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin north
USER north
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "north.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
