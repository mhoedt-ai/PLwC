FROM node:22.23.2-bookworm-slim@sha256:4d676821dff059fd00d277ee4261ef34ea712317fed0737c03941481b5760c96

ARG OCI_CREATED="1970-01-01T00:00:00Z"
ARG SOURCE_REVISION="unknown"
ARG SOURCE_DATE_EPOCH="0"

LABEL org.opencontainers.image.title="PLwC Node Runner" \
      org.opencontainers.image.description="Offline Node sandbox runtime for PLwC" \
      org.opencontainers.image.source="https://github.com/mhoedt-ai/PLwC" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.created="${OCI_CREATED}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"

# Minimal Node 22 LTS sandbox image for plwc_sandbox_run(lang="node").
# The sandbox executes node directly. Package managers from the upstream image
# are deliberately removed because dependency installation is forbidden here.
# Non-root uid/gid 65532 is enforced at runtime via --user 65532:65532.
RUN rm -rf \
        /usr/local/lib/node_modules/corepack \
        /usr/local/lib/node_modules/npm \
        /opt/yarn-v1.22.22 \
    && rm -f \
        /usr/local/bin/corepack \
        /usr/local/bin/npm \
        /usr/local/bin/npx \
        /usr/local/bin/yarn \
        /usr/local/bin/yarnpkg \
    && dpkg --purge --force-remove-essential --force-depends perl-base \
    && test ! -e /usr/bin/perl \
    && ! dpkg-query -W perl-base \
    && rm -f /var/log/dpkg.log

WORKDIR /work
