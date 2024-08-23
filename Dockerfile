FROM python:3.12-slim-bullseye

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml .

RUN uv pip install -r pyproject.toml

COPY . .

COPY .env .env

RUN uv pip install -e .

ENTRYPOINT ["uv", "run", "fastapi", "run", "app.main:app"]