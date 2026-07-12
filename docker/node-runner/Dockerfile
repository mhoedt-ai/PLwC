FROM node:22-slim

# Minimal Node 22 LTS sandbox image for plwc_sandbox_run(lang="node").
# No extra packages — user supplies node_modules in the workspace mount.
# Non-root uid/gid 65532 is enforced at runtime via --user 65532:65532.
WORKDIR /work
