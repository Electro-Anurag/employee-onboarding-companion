# M0 build proposal. Build requires lockfiles created and committed during qualification.
FROM node:22-bookworm-slim AS ui
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS web
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ backend/
COPY manage.py ./
COPY --from=ui /app/backend/static/ backend/static/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["gunicorn", "backend.config.wsgi:application", "--bind", "0.0.0.0:8000"]
