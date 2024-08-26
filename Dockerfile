FROM python:3.12-slim-bullseye

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1

COPY . .

# COPY .env .env

RUN uv pip install -r pyproject.toml

ENTRYPOINT ["uv", "run", "fastapi", "run"]