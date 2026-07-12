# plwc-node-runner

Minimal Docker image for `plwc_sandbox_run(lang="node")`.

## Build

```bash
docker build -t plwc-node-runner:0.1.0 docker/node-runner/
```

## Notes

- Based on `node:22-slim` (Node 22 LTS).
- No extra npm packages are installed — the caller supplies `node_modules`
  inside the workspace mount (`/work`).
- The gateway enforces `--user 65532:65532`, `--network none`, `--read-only`,
  `--cap-drop ALL`, `--security-opt no-new-privileges` at runtime.
  These flags are server-owned and cannot be changed by the model.
- `/tmp` is mounted `noexec`. Scripts that write executable temp files will
  fail — this is expected and correct behavior.
- Run `node`, never `npm`. The sandbox entrypoint is always
  `node <workspace-relative-script.js>`.
- The image must be built locally before first use. PLwC does not pull images
  at runtime (`--pull never`).
