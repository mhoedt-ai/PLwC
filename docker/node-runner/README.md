# plwc-node-runner

Minimal Docker image for `plwc_sandbox_run(lang="node")`.

## Build

The release repository is `ghcr.io/mhoedt-ai/plwc-node-runner` with version
label `0.1.0`. Release execution uses only the full digest stored in the
installer-hashed r27 runtime-image manifest.

## Notes

- Based on the digest-pinned Node 22.23.2 Bookworm Slim image recorded in
  `docker/runtime-image-sources.json`.
- The upstream `npm`, `npx`, `corepack` and `yarn` installations are removed.
  The caller may supply already reviewed `node_modules` inside the workspace
  mount (`/work`); the sandbox cannot install dependencies itself.
- The gateway enforces `--user 65532:65532`, `--network none`, `--read-only`,
  `--cap-drop ALL`, `--security-opt no-new-privileges` at runtime.
  These flags are server-owned and cannot be changed by the model.
- `/tmp` is mounted `noexec`. Scripts that write executable temp files will
  fail — this is expected and correct behavior.
- Run `node`, never `npm`. The sandbox entrypoint is always
  `node <workspace-relative-script.js>`.
- The r27 installer may acquire the manifest-locked GHCR digest only after the
  user explicitly opts in. Gateway execution never pulls images (`--pull never`).
