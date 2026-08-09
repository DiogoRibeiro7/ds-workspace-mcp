FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_DATA_ROOT=/app/data \
    MCP_REPORTS_ROOT=/app/reports

ENV POETRY_VERSION=2.2.1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
COPY data ./data

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi \
    && mkdir -p /app/data /app/reports \
    && groupadd --system app \
    && useradd --system --uid 10001 --gid app --home-dir /app app \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["ds-workspace-mcp"]
