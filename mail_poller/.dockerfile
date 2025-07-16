FROM python:3.12-alpine as builder

WORKDIR /opt

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --upgrade pip wheel setuptools poetry==2.1.1

RUN --mount=type=cache,target=/root/.cache/poetry \
    poetry install --no-root

FROM python:3.12-alpine

WORKDIR /app

ENV VIRTUAL_ENV=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY mail_poller/src/* ./