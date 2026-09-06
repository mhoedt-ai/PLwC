FROM python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af

ARG OCI_CREATED="1970-01-01T00:00:00Z"
ARG SOURCE_REVISION="unknown"
ARG SOURCE_DATE_EPOCH="0"

LABEL org.opencontainers.image.title="PLwC Python Runner" \
      org.opencontainers.image.description="Offline Python sandbox runtime for PLwC" \
      org.opencontainers.image.source="https://github.com/mhoedt-ai/PLwC" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.created="${OCI_CREATED}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

WORKDIR /work
