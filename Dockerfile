FROM python:3.12-slim AS builder

# Install Poetry
ARG POETRY_VERSION=1.8

ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Tell Poetry where to place its cache and virtual environment
ENV POETRY_CACHE_DIR=/opt/.cache

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
RUN --mount=type=cache,target=/opt/.cache poetry install --no-root --without dev

COPY README.md /app/README.md
COPY label_studio_slack_reporter /app/label_studio_slack_reporter
RUN poetry install --only main

# Now let's build the runtime image from the builder.
#   We'll just copy the env and the PATH reference.
FROM python:3.12-slim AS runtime

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV E4E_DOCKER=1

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/label_studio_slack_reporter /app/label_studio_slack_reporter

ENTRYPOINT ["label_studio_reporting_service"]