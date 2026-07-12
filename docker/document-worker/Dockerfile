FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/plwc-document-worker \
    PIP_NO_INDEX=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/plwc-document-worker

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        libcairo2 \
        libffi8 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-doc-worker.txt requirements-doc-worker.txt
COPY requirements-doc-worker.lock requirements-doc-worker.lock
COPY wheelhouse/ /opt/plwc-wheelhouse/
COPY worker/ /opt/plwc-document-worker/

# The lock file must contain pinned versions and hashes generated from the
# offline wheelhouse. This intentionally fails if hashes or wheels are missing.
RUN python -m pip install --no-index --find-links=/opt/plwc-wheelhouse --require-hashes -r requirements-doc-worker.lock

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin plwcworker
USER plwcworker

WORKDIR /work
ENTRYPOINT ["python", "-m", "plwc_document_worker"]
