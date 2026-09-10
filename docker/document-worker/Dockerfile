FROM python:3.12.14-slim-trixie@sha256:2fe5997d249a808b8eeea52c58a1dbffbba28754dc11699ef5c029f2d818ce79

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
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260909T000000Z trixie main' \
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260909T000000Z trixie-updates main' \
        'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20260909T000000Z trixie-security main' \
        > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core=2.37-8 \
        libcairo2=1.18.4-1+b1 \
        libffi8=3.4.8-2 \
        libgdk-pixbuf-2.0-0=2.42.12+dfsg-4+deb13u1 \
        libglib2.0-0t64=2.84.4-3~deb13u3 \
        libpango-1.0-0=1.56.3-1 \
        libpangoft2-1.0-0=1.56.3-1 \
        libpcre2-8-0=10.46-1~deb13u1 \
        shared-mime-info=2.4-5+b2 \
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
    && chage -d 0 plwcworker \
    && dpkg --purge --force-remove-essential --force-depends perl-base \
    && test ! -e /usr/bin/perl \
    && ! dpkg-query -W perl-base \
    && rm -f /var/log/dpkg.log
USER 10001:10001

WORKDIR /work
ENTRYPOINT ["python", "-m", "plwc_document_worker"]
