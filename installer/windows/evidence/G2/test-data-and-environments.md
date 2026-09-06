# G2 test data, environments and redaction - r27

Date: 2026-09-05

Status: **APPROVED**

## Synthetic automated fixtures

- `tests/fixtures/runtime-images/valid.json`: exactly three synthetic locked
  GHCR digests and evidence hashes.
- One mutation fixture per manifest invariant: tag-only, `latest`, wrong owner,
  wrong registry/platform, malformed digest, duplicate ID/repository, mismatched
  reference, missing/zero sizes and missing evidence hash.
- `tests/fixtures/fake-docker/`: executable test double controlled by a JSON
  scenario, emitting only synthetic digests and paths.
- `tests/fixtures/diagnostics/`: bounded sample stdout/stderr, invalid UTF-8,
  over-limit data, control characters and unmistakably fake secrets such as
  `TEST_TOKEN_DO_NOT_USE_0001`.
- Existing clean/r25 Windows fixtures are retained; a sanitized r26
  `worker_missing` fixture is added without real usernames, profiles, UNC
  locations or transcripts.

No fixture contains a live token, Docker credential, browser profile, real
workspace/profile, personal log or source-machine absolute path.

## Disposable Windows 11 matrix

| Environment | Initial state | Required observations |
| --- | --- | --- |
| `W11-A-CLEAN-DOCKER` | Current supported Windows 11; Docker Desktop/WSL2 ready; no PLwC images/files | decline and accepted anonymous image flow, all real operations |
| `W11-B-CLEAN-NODOCKER` | Current Windows 11; no Docker/WSL prepared; no PLwC | Docker opt-in, licensing/UAC, first start/restart, then separate image consent |
| `W11-C-R26-MISSING-WORKER` | exact r26 installed, Bridge/Gateway active, Document Worker absent | r26 defect reproduction, r27 preflight/report, byte-preserved profile/workspace, image recovery |
| `W11-D-R25-UPGRADE` | retained sanitized r25 fixture/runtime | migration, rollback and successful r27 state |
| `W11-E-NETWORK-FAULT` | clean Docker; controlled DNS/proxy/TLS/offline faults | no credential fallback, one error, Safe Mode, new-click retry |
| `W11-F-STANDARD-USER` | standard user; separate admin credential available | original-user path/registry ownership across elevation |
| `W11-G-LOW-DISK` | clean Docker; disposable volume below required size | stop before pull/write and complete report |
| `W11-H-UI-DE` | 1366x768, 100% scaling, German display language | complete German bounds/screenshots and longest strings |
| `W11-I-UI-EN` | 1366x768, 100% scaling, English display language | complete English bounds/screenshots and longest strings |

Each starts from an immutable snapshot and is destroyed/reverted after the
test. Network faults use an isolated virtual network or proxy fixture. No test
changes the developer workstation, a family member's installation or a
non-disposable Docker store.

## Real workload set

After all three locked images are present and probes pass:

- Document Worker probe plus create/validate DOCX, XLSX, PPTX and PDF in a
  disposable workspace;
- governed ZIP create/inspect/extract with traversal rejection;
- `plwc_document_operation` through the one public Gateway;
- Python and Node sandbox scripts with deterministic output;
- repeat all image executions after network is disabled and enforce
  `--pull never`;
- Bridge 8/8 read/write/denial/governance smoke and browser restart/reconnect.

Artifacts are synthetic and deleted only inside the disposable workspace.

## Upgrade and preservation oracle

Before an r25/r26 upgrade, create synthetic profiles and workspace files with
known SHA-256 values, record all selected PLwC/registry paths and active Bridge
state, and remove the Document Worker image from the disposable Docker store.
After failure, retry, success, repair and uninstall, compare:

- profile/workspace file hashes byte-for-byte;
- only owned app/config/state/log/registration changes against the plan;
- no foreign process termination;
- no automatic container image/shared-layer deletion;
- one Gateway, one Bridge child, loopback endpoint and exactly eight tools.

## Redaction oracle

Local diagnostic reports are treated as sensitive. Before any file becomes
repository/release evidence, the evidence builder must:

1. replace user-profile, drive, UNC, temporary and workspace/profile roots with
   stable placeholders;
2. redact token, bearer/basic authorization, cookie, password, secret and
   Docker-auth patterns in keys, values and free text;
3. exclude Docker config, browser data, environment dumps and denylisted files;
4. normalize control characters and cap each captured stream;
5. scan the resulting tree for private path and secret patterns and fail on a
   match;
6. record source hashes privately and exported hashes in `index.json` without
   publishing the private source material.

Manual review samples the final evidence, but automated denylist/secret/path
scans are mandatory and authoritative for the gate.
