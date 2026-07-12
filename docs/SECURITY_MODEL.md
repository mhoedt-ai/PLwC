# PLwC Security Model

This document is the standing reference for PLwC's security posture.
It mirrors the security-notes section of the v0.2.0-rc1 release notes
and is kept consistent with the source. Release notes pin the model
to a specific artifact; this file states it in general terms.

> PLwC is designed as a governed MCP gateway with fail-closed
> boundaries, protected profile/governance files, workspace-scoped
> operations and Docker-based sandboxing. It has been tested against
> the documented threat model, but it is not a formally certified
> security product and cannot protect against a compromised host
> system.

## 1. Principle

**Policy before execution.** Every public tool call goes through:

1. Dispatch validation (operation, scope, lang)
2. Path / parameter validation
3. Protected-boundary check
4. Audit preflight for high-risk operations
5. Adapter execution (filesystem, document worker, sandbox, profile)
6. Result audit

If any step denies, execution does not happen and the result carries a
structured `error_category` so the caller knows why.

## 2. Public boundary

- **One visible MCP server:** `plwc-gateway`. No worker, no Source-A
  bypass server, no raw filesystem server, no second visible MCP.
- **Exactly eight public facade tools:**
  `plwc_status`, `plwc_describe`, `plwc_profile`, `plwc_reflection`,
  `plwc_governor`, `plwc_sandbox_run`, `plwc_workspace_operation`,
  `plwc_document_operation`.
- **Legacy individual tool names are not public** and must remain
  absent from the manifest. Their behaviour is reachable through
  `scope` / `operation` / `lang` dispatch on the facade tools.

## 3. Protected files

The following profile and governance files are protected against
normal workspace tools (`plwc_workspace_operation` and
`plwc_document_operation`):

- `CORE.md`
- `PERSONA.md`
- `TEMPERAMENT.md`
- `CONSCIENCE.md`
- `memory.md`
- `reflection.md`
- `journal.md`
- `compiled_prompt.txt`
- `security.yaml`
- `governance/config.yaml` and other `governance/*.yaml`
- `pending_plan_root` under runtime state

The only governed writers for these files are
`plwc_reflection(operation="write")` and
`plwc_governor(operation="apply")` with `confirmed=true`.

Protected-path checks apply to **both** source and target of any
operation. `plwc_workspace_operation copy`, `move`, `rename` and the
binary read/write paths all reject protected paths in either role.

## 4. Workspace boundary

- All file operations are scoped to `allowed_roots` (from
  `user_config.workspace_path` or the bundled default).
- Parent traversal (`..`), absolute host paths, UNC paths and
  drive-prefixed paths are rejected at the validator.
- Symlink escape is rejected; symlinks pointing outside `allowed_roots`
  do not grant access to their target.
- Cross-profile writes are denied: `plwc_reflection(profile=X)` where
  `X != active_profile` returns `cross_profile_write_denied` without
  mutating the target file.

## 5. Sandbox boundary

- `plwc_sandbox_run` is **Docker-only** for `lang="python"`,
  `lang="shell"` and `lang="node"`. There is no silent host-shell
  fallback.
- `lang="node"` runs a workspace-relative `.js` script with `node`
  inside a separate **`plwc-node-runner:0.1.0`** image (Option B from
  `docs/NODE_SANDBOX_THREAT_MODEL.md`). The Python sandbox image
  (`python:3.12-slim`) is never used for Node execution. Both images are
  static and server-owned; `--pull never` applies to both.
- Docker arguments (image, network, mounts, memory, CPU, pids,
  read-only root, dropped capabilities) are constructed server-side
  from the security config. The model never chooses any Docker flag,
  mount, network mode or privileged setting.
- Node execution uses a dedicated `node_memory` limit (default `768m`;
  V8 idle footprint exceeds CPython). The value remains static and
  server-owned.
- `--network none` is enforced for all sandbox langs; no network access
  of any kind is available inside the container.
- Workspace mount is read-write inside the sandbox; everything else is
  read-only (`--read-only`).
- `/tmp` is mounted `noexec,nosuid,nodev`; scripts that write executable
  temp files will fail. This is correct behavior and must not be
  relaxed.
- Node execution runs `node <script>`, never `npm`. Running npm would
  invite lifecycle-script execution semantics unnecessary for the use
  case.
- If Docker is missing, stopped, disabled or otherwise misconfigured,
  `plwc_status` reports the state clearly (`docker_missing`,
  `docker_daemon_not_running`, `disabled`) and the affected document /
  sandbox operations fail loud. Missing Docker is **never** silently
  bypassed. A missing Node image is separately reported via
  `node_image_available=false` in `plwc_status(scope=sandbox)` and
  fails loud in `plwc_sandbox_run(lang=node)` without falling back to
  the Python sandbox.

## 6. Document worker boundary

- The document worker runs **inside a controlled Docker image**
  (`plwc-document-worker:0.1.0`), built from a pinned offline
  wheelhouse with explicit hashes. There is no runtime PyPI access.
- All worker paths are validated under `/work/...` inside the
  container; the validator rejects absolute paths, parent traversal,
  protected segments and UNC paths.
- Image and DOCX/PPTX/PDF embedding accepts **only** workspace-relative
  PNG/JPEG paths. No external URLs, no `file://`, no `data:` URLs, no
  host-absolute paths.
- Office macros (`.docm` / `.xlsm` / `.pptm`) are not executed.
- `edit_docx` edits an existing `.docx` only through **declarative** edit
  operations (`replace_text`, `set_core_property`, `append_paragraph`,
  `set_footer_text`, `set_header_text`); it never ingests raw XML, raw
  HTML/CSS, formula-like or other active-content strings. `.docm` inputs and
  detected macro payloads are rejected, document XML is parsed only with
  `defusedxml`, and edits are bounded (max 200 ops, bounded input/output size).
  It is **read-A→write-B**: the input file is read-only, the output must be a
  new path, and `overwrite=true` is denied — no in-place mutation.
- Spreadsheet formulas are written as literals and not executed.
- External relationships in OOXML packages are rejected as
  `unsafe_external_relationship`.
- ZIP operations enforce: Zip-Slip / absolute / UNC / protected-target
  / encrypted-entry / symlink rejections; bounded file count, total
  uncompressed size, single-file size, path length, nested-depth and
  compression-ratio limits.
- `extract_zip` into an existing workspace directory merges files but
  refuses any per-file collision with a `destination_file_exists`
  error and lists the conflicting paths.
- Binary workspace ops (`copy`, `read_binary`, `write_binary`) enforce
  a configurable cap (`workspace_binary_max_bytes`, default 100 MiB,
  configurable via `PLWC_WORKSPACE_BINARY_MAX_BYTES`).

## 7. Reflection and governor boundary

- `plwc_reflection(operation="write")` writes only into the active
  profile's `reflection.md`. Cross-profile writes are denied.
- `plwc_governor(operation="apply")` requires `confirmed=true` to
  mutate any protected file. Plan/apply are split: planning does not
  mutate; apply only mutates after explicit confirmation.
- `force=true` is an admin override for **threshold-style** denials
  on `memory_promotion` and `persona_promotion`
  (`insufficient_marker`, `insufficient_evidence`). `force` does
  **not** bypass quality gates: semantic rejection, insufficient
  trust, duplicate detection, conflict review and cross-profile
  denial are unaffected. `force=true` still requires `confirmed=true`
  in apply. Every applied override is recorded in `journal.md` as
  `admin_override_applied=true`.
- `reflection_condensation` apply by `plan_id` reads from a
  `pending_plan_root` outside both `allowed_roots` and `profile_root`.
  The plan is hash-checked; unknown / wrong-type / cross-profile /
  tampered plan ids are denied.

## 8. Audit

- A local `audit.jsonl` records all high-risk operations.
- Path is configurable; secrets are redacted before logging.
- No remote audit channel; no telemetry; no network calls during audit.

## 9. Tested scope

The current public release (v0.2.0-rc1) has been tested against the
threat model in the following areas:

- workspace boundary (`allowed_roots`, parent traversal, absolute /
  UNC / drive-prefixed paths, protected segments);
- profile and governance boundary (protected files cannot be edited
  through workspace or document operations);
- public-tool boundary (exactly eight facade tools; legacy 19 names
  absent);
- traversal and unsafe-path inputs across workspace, document and ZIP
  paths (Zip-Slip, encrypted, symlink, size, file count, path length,
  compression ratio);
- sandbox boundary (Docker-only Python and shell, no host-shell
  fallback);
- reflection and governor boundary (cross-profile denial,
  unconfirmed-apply denial, `reflection_condensation` `plan_id`
  hash-checked apply).

## 10. Non-claims

PLwC explicitly does **not** claim:

- formal security certification;
- third-party security audit;
- complete isolation against all host-level attacks;
- malware containment or behaviour as a malware sandbox;
- production security certification of any kind.

In particular, PLwC **cannot** protect against:

- a compromised host operating system;
- a compromised user account or shell;
- a compromised Docker engine;
- a tampered Claude Desktop installation;
- side-channel attacks on Docker isolation;
- hardware-level attacks.

PLwC is **not** a malware sandbox: hostile code executed inside the
Docker sandbox is bounded by Docker's isolation, not by a malware-grade
containment layer.

## 11. Artifact signing

The MCPB artifact is currently **not signed**. Artifact signing is not
part of the v0.2 release pipeline. Until signing is added, the
authoritative integrity check is the SHA256 of the released MCPB,
which is recorded in the corresponding `docs/RELEASE_NOTES_*.md` and
in the GitHub Draft pre-release entry.

## 12. Risk acceptance

Remaining risks are known, documented and accepted for the current
Release Candidate. They are recorded as Release Candidate notes, not
as release blockers, and they will be revisited before any final
v0.2.0 release decision.

This file is the standing reference. Per-RC residual risks and any
deltas from this baseline are recorded in the corresponding
`docs/RELEASE_NOTES_*.md`.
