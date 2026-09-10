FROM python:3.12.14-slim-trixie@sha256:2fe5997d249a808b8eeea52c58a1dbffbba28754dc11699ef5c029f2d818ce79

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

# Perl is not a PLwC runtime dependency. Removing the incidental Debian
# essential package eliminates an otherwise executable, unused interpreter.
RUN dpkg --purge --force-remove-essential --force-depends perl-base \
    && test ! -e /usr/bin/perl \
    && ! dpkg-query -W perl-base \
    && rm -f /var/log/dpkg.log

WORKDIR /work
