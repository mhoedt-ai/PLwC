FROM python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af

ARG OCI_CREATED="1970-01-01T00:00:00Z"
ARG SOURCE_REVISION="unknown"
ARG SOURCE_DATE_EPOCH="0"

LABEL org.opencontainers.image.title="PLwC Document Worker" \
      org.opencontainers.image.description="Offline governed document operations for PLwC" \
      org.opencontainers.image.source="https://github.com/mhoedt-ai/PLwC" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.created="${OCI_CREATED}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/plwc-document-worker \
    PIP_NO_INDEX=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

WORKDIR /opt/plwc-document-worker

RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260806T000000Z bookworm main' \
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260806T000000Z bookworm-updates main' \
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20260806T000000Z bookworm-security main' \
        > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core=2.37-6 \
        libcairo2=1.16.0-7 \
        libffi8=3.4.4-1 \
        libgdk-pixbuf-2.0-0=2.42.10+dfsg-1+deb12u4 \
        libglib2.0-0=2.74.6-2+deb12u9 \
        libpango-1.0-0=1.50.12+ds-1 \
        libpangoft2-1.0-0=1.50.12+ds-1 \
        shared-mime-info=2.2-1 \
    && rm -rf \
        /var/lib/apt/lists/* \
        /var/cache/apt/* \
        /var/cache/ldconfig/* \
        /var/log/apt/* \
        /var/log/alternatives.log \
        /var/log/dpkg.log

COPY requirements-doc-worker.txt requirements-doc-worker.txt
COPY requirements-doc-worker.lock requirements-doc-worker.lock
COPY wheelhouse/ /opt/plwc-wheelhouse/
COPY worker/ /opt/plwc-document-worker/

# The lock file must contain pinned versions and hashes generated from the
# offline wheelhouse. This intentionally fails if hashes or wheels are missing.
RUN python -m pip install --no-index --find-links=/opt/plwc-wheelhouse --require-hashes -r requirements-doc-worker.lock

RUN useradd --no-log-init --no-create-home --uid 10001 --shell /usr/sbin/nologin plwcworker \
    && chage -d 0 plwcworker
USER 10001:10001

WORKDIR /work
ENTRYPOINT ["python", "-m", "plwc_document_worker"]
