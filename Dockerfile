# Two stages: the Vite build of web/, then the Python image that serves it (D2).

# Web: Vue 3 + Vite build. The shell has no data; everything comes from the API.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci
COPY web ./
RUN npm run build

# API: FastAPI on uvicorn, serving /api and the web build with SPA fallback.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
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
