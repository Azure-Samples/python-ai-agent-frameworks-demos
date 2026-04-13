FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt /tmp/pip-tmp/

RUN uv pip install --system --no-cache -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp
