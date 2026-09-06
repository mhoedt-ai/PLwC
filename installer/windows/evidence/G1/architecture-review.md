# G1 architecture review - Windows Installer r27

Date: 2026-09-05

Status: **PASS / GO TO G2**

Scope: the r27 correction for controlled delivery of the three PLwC runtime
images and complete installer diagnostics. This review does not authorize a
GHCR push, public package visibility, a production installer build, or a
release.

## Reviewed baseline

- r26 only calls `docker image inspect` for three tag-only references. It does
  not pull, load, or build an image.
- A real Windows 11 installation reached a working Gateway and Bridge but a
  document call failed with `UNAVAILABLE/worker_missing`.
- A separate r26 preflight failure displayed a JSON report path, while the
  supplied diagnostic export did not contain that report.
- The current Document Worker and Node Runner Dockerfiles use mutable base
  tags; the Document Worker also resolves Debian packages at build time.
- Runtime defaults currently duplicate mutable/tag-only references in Gateway
  code and example configuration.

The two field findings remain separate defects: successful image delivery
cannot explain an unreported preflight exception, and better diagnostics do
not provide a missing image.

## Approved architecture

### 1. One immutable runtime-image contract

`installer/windows/manifests/runtime-images.json` is the single release lock
for Installer and Gateway. Its schema is
`installer/windows/manifests/runtime-images.schema.json`. The G3 build creates
the lock only after the image artifacts and their registry digests exist.

Each of the exactly three entries binds:

- logical ID: `document_worker`, `node_runner`, or `python_runner`;
- registry and repository under `ghcr.io/mhoedt-ai`;
- display tag and semantic version;
- immutable `sha256` manifest digest and complete `repository@sha256:` pull
  reference;
- platform `linux/amd64`;
- compressed download bytes and unpacked content bytes;
- OCI source, revision, version, title, description, licenses and created
  labels;
- SBOM, licence inventory, vulnerability report and provenance references plus
  their SHA-256 hashes;
- a fixed, server-owned probe command and its expected structured result.

Schema rules reject extra properties, another registry/owner, `latest`, a
tag-only pull reference, a non-SHA-256 digest, duplicate IDs/repositories,
another platform, dynamic commands and missing evidence hashes. The manifest
itself is part of the installer payload manifest and is SHA-256 checked before
use.

`src/plwc_gateway/runtime_images.py` will be the only Gateway loader for this
contract. Adapters receive immutable references from it; the model cannot
provide an image, entry point or Docker flag. Known legacy release defaults
(`python:3.12-slim`, `plwc-node-runner:0.1.0`, and
`plwc-document-worker:0.1.0`) are migrated to their locked r27 entries. An
unknown configured image is not silently pulled and leaves the affected
operation unavailable with a diagnostic reason.

The byte-identical installed lock lives at
`<AppPath>/installation/runtime-images.json`; the installed payload manifest
owns it and records its SHA-256. `selection.ini` stores only consent/outcome
facts and never duplicates image references. The shared settings retain
feature switches but do not become a second image catalog.

### 2. Image build boundary

PLwC owns and publishes these repositories only:

- `ghcr.io/mhoedt-ai/plwc-document-worker`
- `ghcr.io/mhoedt-ai/plwc-node-runner`
- `ghcr.io/mhoedt-ai/plwc-python-runner`

All target `linux/amd64`. `docker/python-runner/Dockerfile` becomes the
PLwC-owned replacement for the direct `python:3.12-slim` runtime dependency.
Every `FROM` uses a reviewed digest. Debian packages are obtained from a fixed
snapshot and an exact package/version lock; the build fails if the snapshot or
versions cannot be reproduced. Python packages continue to be installed from
an offline, hash-locked wheelhouse. Node and Python runners add no package at
runtime.

`scripts/build_document_worker_wheelhouse.py` restores the documented
wheelhouse process. `scripts/build_runtime_images.py` builds the three OCI
artifacts from a clean checkout, and `scripts/verify_runtime_images.py` checks
metadata, platform, root user policy, offline probes, SBOM/licence/scan/
provenance bindings and two-build equality. G3 must compare OCI manifest
digests from two independent clean build directories; a local Docker image ID
is not a release digest.

The GitHub Actions publisher is manual, uses SHA-pinned third-party actions,
minimal `contents: read` and `packages: write` permissions, and pushes only the
already verified commit and version. A workflow run does not make packages
public. Push, visibility change and production build require separate Product
Owner approvals.

### 3. Installer flow and consent

The image choice is a separate bilingual checkbox after Docker status is known.
It is visible only when the Docker daemon is reachable, starts unchecked, and
is never inferred from component selection, an earlier installer revision or
silent mode. The page shows all three purposes, exact source, versions,
platform, known download total, unpacked storage total, network requirement
and the Safe Mode consequence of declining.

The page object is `RuntimeImagesPage`, positioned after the existing
prerequisite action/recheck flow and before directory/configuration pages. It
uses one Boolean checkbox, a read-only vertically scrollable details control
and the fixed `Weiter`/`Next` navigation button. At `1366x768` its controls fit
inside the page surface; long repository/digest values wrap or scroll and
never widen the page. The complete new `CustomMessage` inventory is:

- `PageRuntimeImagesTitle`, `PageRuntimeImagesDescription`,
  `PageRuntimeImagesSubCaption`;
- `OptionInstallRuntimeImages`, `RuntimeImagesSource`,
  `RuntimeImagesPlatform`, `RuntimeImagesVersions`;
- `RuntimeImagesDownloadSize`, `RuntimeImagesDiskSize`,
  `RuntimeImagesConsentRequired`, `RuntimeImagesDeclinedSafeMode`;
- `RuntimeImagesProgressInventory`, `RuntimeImagesProgressPull`,
  `RuntimeImagesProgressVerify`, `RuntimeImagesProgressProbe`;
- `RuntimeImagesCancelled`, `RuntimeImagesFailed`,
  `RuntimeImagesRetry`, `RuntimeImagesReady`, and
  `RuntimeImagesReportLocation`.

Every ID has German and English values; the static string contract fails if a
key is absent, identical by accidental fallback, or contains mixed-language
installer text. When Docker is not reachable the choice is not actionable and
the prerequisite report/summary uses the existing localized Safe Mode branch.

Before any pull the Installer reruns all non-mutating prerequisites, validates
the embedded lock and available disk space, and writes an acquisition plan.
`installer/windows/assets/runtime-image-manager.py` then receives only the
manifest path, Docker executable, report directory, operation and explicit
consent token. It constructs `subprocess` argument arrays; it never accepts a
repository, image, probe command or Docker option from UI/model input.

For each image in manifest order:

1. inspect the exact `repository@digest` locally;
2. if absent and consent exists, run `docker pull --platform linux/amd64` for
   that exact reference;
3. inspect `RepoDigests`, OS and architecture and require the locked digest;
4. run the fixed probe with `--pull never --network none`, non-root user,
   read-only root, dropped capabilities, no-new-privileges and bounded CPU,
   memory, PIDs and time;
5. persist the individual state and only then continue.

The allowed state transitions are:

```text
present -> verified -> probe_passed
download_required -> pulling -> verified -> probe_passed
any non-terminal state -> failed | safe_mode
pulling -> cancelled -> safe_mode
```

The aggregate is Docker-ready only when all three entries are
`probe_passed`. A matching local digest avoids a download but never avoids the
real probe. A tag pointing at a different image is ignored, not retagged or
deleted. A partial successful pull may remain in Docker's content store; it is
recorded as such and is never claimed as a completed PLwC image set.

The manager runs under the original user context and uses the current Docker
Desktop named-pipe context. It performs no registry login, credential write,
Docker configuration mutation or daemon reconfiguration. Public anonymous
pull is an acceptance requirement, not a token fallback.

### 4. Cancellation, retry and Safe Mode

The long-running image operation uses a cancellable process wrapper rather
than the current blocking `Exec(... ewWaitUntilTerminated ...)` path. The
Installer keeps its Cancel control responsive, signals a manager-owned cancel
file, and the manager terminates only the Docker child it created. Each pull
has a bounded inactivity and total timeout. A new attempt requires a new user
click and a new plan ID; no automatic retry starts another pull.

Decline, unavailable Docker, cancellation, timeout, pull error, digest mismatch
or probe failure results in an explicit per-image explanation and
`safe_mode_expected=true`. Core files, profile and workspace may still be
installed. The summary names Document Worker, Node Sandbox and/or Python
Sandbox as unavailable. It never displays a full-success Docker claim.

The configuration UI may later offer the same plan/confirm/apply contract for
repair. It must reuse the installed immutable manifest and the image manager;
it must not implement a second pull path.

### 5. Transaction and data ownership

Image acquisition occurs before the file transaction and cannot write a
profile, workspace or host-client configuration. Installer preflight still
protects the existing runtime before file replacement. Installation state
records the exact per-image outcome, but never treats a Docker layer as an
exclusively owned user file.

Upgrade and repair are idempotent by digest. Uninstall removes PLwC files and
registrations that are listed as owned, but does not delete images, tags,
shared layers, Docker Desktop or user data. Image removal requires a separate,
explicit maintenance plan outside normal uninstall.

### 6. Diagnostics

All Installer child execution moves behind the process/report contract in
`diagnostic-design.md`. The maintenance helper catches unexpected `Exception`
at its outer boundary and atomically writes a report before returning a stable
exit code. The Inno layer verifies that the report exists before displaying
its path. The Doctor inventories and exports all r27 setup reports rather than
only the legacy installer log.

## Module ownership

| Responsibility | Planned object |
| --- | --- |
| Runtime image schema and lock | `installer/windows/manifests/runtime-images.schema.json`, `runtime-images.json` |
| Image acquisition/probes/reporting | `installer/windows/assets/runtime-image-manager.py` |
| Installer UI/state/orchestration | `installer/windows/PLwCSetup.iss` |
| Maintenance process reporting | `installer/windows/assets/installer-maintenance.py` |
| Runtime manifest loading | `src/plwc_gateway/runtime_images.py` |
| Document Worker runtime | `src/plwc_gateway/adapters/document_worker.py` |
| Python/Node sandbox runtime | `src/plwc_gateway/config/settings.py`, sandbox adapter |
| Image build and verification | `scripts/build_runtime_images.py`, `scripts/verify_runtime_images.py` |
| Wheelhouse production | `scripts/build_document_worker_wheelhouse.py` |
| GHCR publisher | `.github/workflows/runtime-images.yml` |
| Diagnostic inventory/export | `src/plwc_gateway/installation/doctor.py`, configuration UI service |

## Review against G1 exit criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| Components, directories, config mapping and ownership specified | PASS | This review and `payload-boundary.md` |
| Docker/image probes and UI/summary states specified | PASS | This review and `container-image-design.md` |
| Opt-in, registry, versions/digests, cancellation/error/recheck specified | PASS | This review |
| German/English page and Boolean control specified | PASS | Separate unchecked bilingual checkbox; G2 inventories strings and bounds |
| One Gateway and Bridge boundaries preserved | PASS | No host/Bridge architecture change; immutable runtime loader only |
| Payload allowlist and privacy denylist approved | PASS | `payload-boundary.md` |
| Security, Safe Mode and rollback reviewed | PASS | `threat-review.md` and this review |
| Diagnostics complete by design | PASS | `diagnostic-design.md` |

Decision: **G1 PASS / GO TO G2**. No unresolved G1 security, ownership or UX
decision remains. Implementation is still prohibited until G2 supplies a test
for every requirement and is marked GO.
