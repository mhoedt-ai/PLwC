# plwc-python-runner

Minimal Python 3.12 image for `plwc_sandbox_run(lang="python")`.

The release build uses the digest-pinned base in `Dockerfile` and publishes the
result as `ghcr.io/mhoedt-ai/plwc-python-runner:0.1.0`. Runtime execution uses
the complete digest from the r27 runtime-image lock, with `--pull never`,
`--network none`, a read-only root, dropped capabilities, no-new-privileges and
UID/GID 65532.

No package is installed at runtime. User code can import only modules already
present in the fixed image or supplied under the governed workspace mount.
