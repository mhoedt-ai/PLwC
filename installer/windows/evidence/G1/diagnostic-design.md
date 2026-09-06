# G1 diagnostic and failure-report design - r27

Date: 2026-09-05

Status: **APPROVED FOR TEST DESIGN**

## Problem being corrected

r26 can display a preflight JSON path after Python exits with code 1 even when
that JSON file was never produced or included in the collected diagnostics.
The current Inno wrapper records only whether `Exec` started and the exit code;
it does not preserve child stdout/stderr. The maintenance helper catches a
limited exception set, so an unexpected exception may escape before a report
is written. Doctor currently inventories only the launcher log, installer log
and audit log.

## One child-process envelope

Every maintenance, migration, acquisition and probe child produces a closed
JSON envelope with at least:

```json
{
  "schema_version": "1.0.0",
  "report_id": "sha256-of-canonical-report-content",
  "build_id": "...installer-r27...",
  "phase": "preflight|transaction|image_inventory|image_pull|image_probe|postflight|rollback",
  "category": "maintenance|docker|probe",
  "command_id": "allowlisted symbolic id",
  "started": true,
  "started_at": "UTC ISO-8601",
  "finished_at": "UTC ISO-8601",
  "duration_ms": 0,
  "exit_code": 0,
  "timed_out": false,
  "cancelled": false,
  "stdout": "bounded redacted text",
  "stderr": "bounded redacted text",
  "stdout_truncated": false,
  "stderr_truncated": false,
  "exception_type": null,
  "error_category": null,
  "report_path": "absolute local path",
  "ok": true
}
```

The actual executable/arguments are represented in persisted output only by a
symbolic command ID and a redacted argument summary. Full GHCR digest is safe;
tokens, authorization headers and environment values are never included.
stdout/stderr are decoded with replacement, control characters normalized,
redacted, and capped independently at 64 KiB. Environment is an explicit
allowlist rather than a dump.

## Atomicity and fallback

- Before starting a child, write an atomic `started=false/pending` envelope.
- Immediately after successful process creation, replace it with
  `started=true/running`.
- On completion, timeout or cancellation, atomically replace it with the final
  envelope after flushing captured output.
- The Python top level catches `Exception` after arguments and fallback report
  location are established. It writes `exception_type`, categorized message
  and exit 40 before exiting. `KeyboardInterrupt` maps to cancellation; normal
  `SystemExit` preserves its intended code.
- If the primary report cannot be written, write a minimal fallback beside
  `installer-diagnostic.log`; if that also fails, Inno records the two failed
  paths in its own log but displays no nonexistent report as if it exists.
- Inno calls `FileExists` and a minimal schema/report-ID check before adding a
  report path to an error dialog. Otherwise it displays the existing setup log
  directory and a localized `report could not be created` statement.

Stable exit categories:

| Exit | Meaning |
| --- | --- |
| 0 | success |
| 20 | expected preflight/plan block |
| 21 | invalid/tampered image manifest |
| 22 | Docker CLI/daemon unavailable |
| 23 | pull or digest/platform verification failed |
| 24 | runtime probe failed |
| 25 | user cancellation or bounded timeout (distinguished in JSON) |
| 30 | hard postflight failure |
| 40 | unexpected helper/process error with report |
| 50 | rollback incomplete |

## Required report inventory

Under the configured PLwC logs/state roots, r27 uses revisioned names:

- `logs/setup/installer-diagnostic.log`
- `logs/setup/r27-installer-preflight.json`
- `state/installation/r27-installer-transaction.json`
- `logs/setup/r27-image-inventory.json`
- `logs/setup/r27-image-acquisition.json`
- `logs/setup/r27-image-processes/*.json`
- `logs/setup/r27-installer-postflight.json`
- `logs/setup/r27-installer-rollback.json`
- existing Bridge launcher log and Gateway audit log.

Reports contain absolute paths because they diagnose the affected machine.
They are private local diagnostics. Repository/release evidence uses a
separate redaction step and may not contain those paths.

## Doctor/export contract

`InstallationDoctor._state_facts()` inventories every fixed report above and
also safely enumerates only `r27-image-processes/*.json` beneath the known
setup root. The diagnostic export is a ZIP with:

- `index.json` listing source path, existence, size, SHA-256, sensitivity and
  redaction status;
- every existing r27 report, transaction and bounded process report;
- installer, Bridge launcher and audit logs after redaction;
- no profiles, workspace files, browser data, environment dump or Docker
  credential file.

Missing optional reports are listed as missing; a report cited by an active
failure is mandatory and makes export validation fail if absent. Export names
are relative and traversal-safe. The UI button exports the ZIP rather than only
the in-memory Doctor diagnosis JSON.

## Installer error presentation

One failing action produces one localized primary message containing:

- component/phase;
- stable error category and exit code;
- whether Safe Mode remains available;
- an existing report or diagnostic-root path;
- retry guidance requiring a new click.

It must not then add a second generic prerequisite-gate dialog for the same
attempt. A failed postflight still triggers the owned file rollback; image
blobs are not deleted. The rollback report is always attempted and linked only
if it exists.

Decision: the design covers expected codes 1/20/30/40/50, new image-specific
codes, unexpected exceptions, report atomicity, redaction and complete export.
G2 must turn every branch into fault-injection tests before implementation.
