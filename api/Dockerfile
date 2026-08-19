# syntax=docker/dockerfile:1.7

FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS dependency-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/opt/poetry/bin:${PATH}"

RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir "poetry==2.3.4" \
    && python -m venv /opt/venv

WORKDIR /build

# Copy dependency definitions first so locked dependency installation is cacheable.
COPY core/pyproject.toml core/poetry.lock core/README.md ./core/
COPY core/src ./core/src
COPY api/pyproject.toml api/poetry.lock api/README.md ./api/
COPY api/src ./api/src

RUN poetry build --directory /build/core --format wheel \
    && poetry build --directory /build/api --format wheel \
    && cd /build/api \
    && poetry install --only main --no-interaction --no-ansi \
    && pip uninstall --yes tlefinder-api tlefinder-core \
    && pip install --no-cache-dir --no-deps \
        /build/core/dist/tlefinder_core-*.whl \
        /build/api/dist/tlefinder_api-*.whl \
    && python -c "import tlefinder.api, tlefinder.core"


FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS runtime

ENV HOME=/tmp \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 tlefinder \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin tlefinder \
    && install --directory --owner=tlefinder --group=tlefinder --mode=0700 /data /tle-cache

COPY --from=dependency-builder /opt/venv /opt/venv

WORKDIR /app

USER tlefinder

EXPOSE 2626

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:2626/healthz', timeout=2).read()"]

CMD ["python", "-m", "tlefinder.api.server"]
