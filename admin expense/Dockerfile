FROM python:3.11-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app


COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


COPY . .

ENV PORT=7860
EXPOSE 7860



CMD ["sh", "-c", "uv run uvicorn expense_agent.fast_api_app:app --host 0.0.0.0 --port ${PORT}"]
