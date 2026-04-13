FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends zstd && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt /tmp/pip-tmp/

RUN uv pip install --system --no-cache -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp
