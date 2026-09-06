# G2 implementation and verification plan - Windows Installer r27

Date: 2026-09-05

Status: **PASS / GO TO IMPLEMENTATION (G3)**

This gate approves test design, not a GHCR push, public package visibility,
production EXE build or release. Tests that need a registry artifact remain
designed but cannot be executed until the corresponding separate approval.

## Test objectives

1. Reproduce both r26 field defects independently: missing Document Worker and
   a preflight child failure whose referenced report must exist.
2. Prove that r27 never pulls an image without current interactive consent.
3. Prove that every installed runtime image is selected by an immutable GHCR
   digest and passes a real networkless probe.
4. Prove deterministic, auditable production of all three images.
5. Prove that decline, offline, cancellation and all failures remain honest
   Safe Mode and preserve profiles/workspaces.
6. Prove complete bilingual diagnostics and export for expected and unexpected
   failures.
7. Re-run the existing installer, Bridge, Gateway, governance, rollback and
   minimum-resolution regression suites.

## Planned automated suites

| Test family | Planned implementation | Primary scope |
| --- | --- | --- |
| `MAN-*` | `tests/integration/test_runtime_image_manifest.py` | closed schema, exact three repositories, digest/reference/platform/evidence invariants |
| `IMG-*` | `tests/integration/test_runtime_image_manager.py` | Fake Docker inventory, consent, pull, inspect, probe, cancellation, retry and Safe Mode |
| `RES-*` | `tests/integration/test_runtime_image_resolution.py` | Gateway single-source lock, legacy mapping, no tag fallback/model override |
| `DIA-*` | `tests/integration/test_installer_diagnostics.py` | process envelope, exception/exit faults, redaction, report existence and export |
| `BLD-*` | `tests/integration/test_runtime_image_build_contract.py` | pinned Dockerfiles, locks, build context, OCI labels/evidence and two-build comparison logic |
| `DOC-*` | `tests/integration/test_document_worker_mvp.py` | worker probe and document operations against immutable image |
| `INS-*` | `installer/windows/tests/installer-contract.Tests.ps1` | Inno order, opt-in default, silent prohibition, fixed refs, pages, sizes and messages |
| `UI-*` | `installer/windows/tests/installer-ui-smoke.ps1` | executable UI at 1366x768, both languages, bounds, navigation and injected branches |
| `REG-*` | existing `tests/integration/*` plus installer suites | selection, paths, settings, transaction, Bridge/Gateway/governance regressions |
| `SCN-*` | `scripts/verify_runtime_images.py` and CI job | SBOM, licences, vulnerability policy, provenance, secrets and reproducibility |

The current suite is extended instead of duplicated where it already owns a
contract. The two README-referenced but missing files,
`scripts/build_document_worker_wheelhouse.py` and
`tests/integration/test_document_worker_mvp.py`, are mandatory G3 work, not
waived documentation drift.

## Test order

1. Static source/schema/string/privacy contracts; no network or Docker.
2. Pure Python unit tests with a Fake Docker executable and synthetic reports.
3. Installer fixture compile and UI smoke; no real vendor install or pull.
4. Clean-checkout image build twice, then local hardened probes with
   `--pull never --network none`.
5. SBOM/licence/secret/vulnerability/provenance verification.
6. After separate push/visibility approval, anonymous GHCR pull by digest.
7. After a candidate build approval, disposable Windows system validation.

Any failure stops the later layer. A passing local image ID never substitutes
for a registry manifest digest or anonymous-pull test.

## Fake Docker contract

The test double accepts only the Docker commands used by the manager and logs
each argument as an array. It can simulate missing CLI, daemon failure, exact
digest present/absent, misleading local tag, wrong RepoDigest/platform,
download progress, authentication challenge, DNS/proxy/TLS error, disk error,
timeout, cancellation, probe output/exit and retry. Tests assert both calls
made and forbidden calls not made.

It must fail the test if it observes:

- `login`, credential/config mutation, a non-GHCR registry or another owner;
- `latest`, tag-only pull/run/inspect or a reference absent from the lock;
- `docker build` on an end-user acquisition path;
- probe without `--pull never`, `--network none` and hardening flags;
- any network action after the first failure or after cancellation;
- shell-string execution instead of a structured argument list.

The full acquisition cases are in `image-acquisition-matrix.csv`.

## Installer and UI contracts

- The image page exists only after a reachable Docker daemon is established,
  is after prerequisite acquisition and before directory/configuration pages.
- Its Boolean is a checkbox and always unchecked at first interactive display.
- Back/forward navigation cannot turn it on. Existing r26 state cannot turn it
  on. `WizardSilent` cannot turn it on and cannot invoke the image manager.
- Rechecking prerequisites is side-effect free. The committed image plan is
  rechecked before acquisition.
- All current 293 `CustomMessages` remain paired and all 20 r27 additions have
  exact German/English expectations in `ui-localization-test-design.md`.
- Bounds/screenshot fixtures cover every page at 1366x768, 100% scale, longest
  digest/repository/error/report text, German and English, forward/backward
  navigation and success/Safe Mode/failure summaries.
- A single acquisition failure produces one primary localized dialog and no
  additional generic gate dialog in the same attempt.

The 16 component selections are fixed in `component-matrix.csv`. Docker image
consent is orthogonal and is tested independently, preventing component
selection from becoming implicit consent.

## Image build and security tests

`BLD-*` statically rejects mutable `FROM`, non-snapshot apt sources, unlocked
package installs, missing wheel hashes, uncontrolled build context and
wall-clock build content. Clean-build tests run in two separate checkouts with
the same source commit and `SOURCE_DATE_EPOCH`, export OCI layouts and compare
manifest/config/layer digests.

`SCN-*` requires for every exact image digest:

- OCI source/revision/version/licence labels;
- SPDX or CycloneDX SBOM and SHA-256;
- normalized licence inventory and SHA-256;
- vulnerability report with timestamp/database identity and no unaccepted
  critical or high finding;
- provenance subject matching the image digest and source commit;
- secret/private-path scan of context, layers, metadata and evidence.

The registry check pulls from a Docker configuration directory with no auth
entry and proves anonymous access. It compares the observed GHCR digest to the
release lock, removes only the disposable test tag/cache, then proves all three
networkless workloads.

## Diagnostic fault injection

`DIA-*` injects process-not-started, raw exit 1, planned exit 20, image exits
21-25, postflight 30, unexpected exception 40, rollback 50, timeout, cancel,
unencodable output, oversized output, secret/control-character output and
primary-report write failure. The expected envelope/export outcomes are in
`diagnostic-fault-matrix.csv`.

Every dialog report path must pass a real file-existence/schema check. Every
active failure report must appear in the exported ZIP index and payload. Local
diagnostics may contain local paths; repository evidence is redacted and then
scanned for private path/token patterns.

## Windows system validation inputs

`test-data-and-environments.md` defines disposable Windows 11 snapshots for:

- Docker ready with no PLwC images;
- Docker installed by Setup and awaiting first daemon/WSL2 start;
- direct r26 to r27 with Bridge active and Document Worker absent;
- r25 to r27 migration;
- offline/DNS/proxy, low disk, cancellation/retry and reboot;
- standard user plus alternate administrator credentials;
- German and English 1366x768 UI.

Only disposable VM snapshots are used for destructive install/repair/uninstall
faults. Named real user profiles or workspaces are never test data.

## Requirement coverage and evidence

`requirement-test-map.csv` contains exactly one row for each of all 27 G0
requirements and at least one automated test ID per row. Manual system
observations complement automation but do not replace an automatable contract.

G4 evidence targets:

- `G4/static-and-unit-results.md`
- `G4/prerequisite-matrix-results.csv`
- `G4/selection-matrix-results.csv`
- `G4/ui-layout-and-localization-results.md`
- `G4/image-acquisition-results.md`
- `G4/image-security-results.md`
- `G4/diagnostic-fault-results.md`
- `G4/payload-scan.md`

G5 evidence targets:

- `G5/windows-system-results.md`
- `G5/ui-acceptance.md`
- `G5/client-smoke-results.md`
- `G5/reboot-reconnect.md`
- `G5/uninstall-upgrade.md`

All evidence records source commit, exact EXE hash where applicable, exact OCI
digests, environment/fixture identity, command, start/end time, exit status,
redaction result and reviewer role.

## G2 review

| Exit criterion | Result |
| --- | --- |
| Every UR/SR has tests | PASS - 27/27 mapped and mechanically checked |
| All 16 selections have expectations | PASS - `component-matrix.csv` |
| Image success/error paths complete | PASS - `image-acquisition-matrix.csv` |
| Expected/unexpected diagnostic faults complete | PASS - `diagnostic-fault-matrix.csv` |
| UI strings, both languages and 1366x768 defined | PASS - `ui-localization-test-design.md` |
| Clean VM, reboot, upgrade, repair, uninstall defined | PASS - `test-data-and-environments.md` |
| Test data and redaction rules defined | PASS - `test-data-and-environments.md` |
| No destructive test targets a non-disposable environment | PASS |
| No automatable critical behavior is manual-only | PASS |

Decision: **G2 PASS / GO TO G3 IMPLEMENTATION**. G3 remains incomplete and no
artifact/publishing approval is implied.
