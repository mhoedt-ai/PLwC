# G1 container image design - r27

Date: 2026-09-05

Status: **APPROVED FOR TEST DESIGN**

## Release image set

| ID | Image | Version | Platform | Fixed probe |
| --- | --- | --- | --- | --- |
| `document_worker` | `ghcr.io/mhoedt-ai/plwc-document-worker` | `0.1.0` | `linux/amd64` | `python -m plwc_document_worker probe` with expected structured capability set |
| `node_runner` | `ghcr.io/mhoedt-ai/plwc-node-runner` | `0.1.0` | `linux/amd64` | `node --version` plus exact major/minimum contract |
| `python_runner` | `ghcr.io/mhoedt-ai/plwc-python-runner` | `0.1.0` | `linux/amd64` | `python --version` plus exact major/minimum contract |

The tags above are human-readable aliases only. No pull, inspect, probe or
runtime command may use them without the manifest digest.

## Build inputs

### Document Worker

- digest-pinned Python 3.12 slim base for `linux/amd64`;
- fixed Debian snapshot with exact native package versions;
- 31-file offline wheelhouse regenerated and verified by script;
- `requirements-doc-worker.lock` with `--require-hashes`;
- repository worker source at the recorded commit;
- non-root UID 10001 and fixed entry point.

### Node Runner

- digest-pinned Node 22 slim base for `linux/amd64`;
- no package-manager or network step;
- work directory `/work`; runtime enforces UID/GID 65532.

### Python Runner

- digest-pinned Python 3.12 slim base for `linux/amd64`;
- no pip/apt network step and no extra packages;
- work directory `/work`; runtime enforces UID/GID 65532.

All Dockerfiles use BuildKit syntax and fail if the target platform is not
`linux/amd64`. Build contexts are allowlisted so local wheel caches, profiles,
logs, secrets and `.git` cannot enter layers.

## Reproducibility contract

1. Resolve upstream base manifest digests once during reviewed source update;
   store them in a committed source lock.
2. For the Document Worker, store Debian snapshot timestamp, repository suite,
   package names, versions and downloaded archive hashes in a committed lock.
3. Regenerate the wheelhouse in an isolated build job; require the committed
   wheel manifest and lock to match every filename, size and SHA-256.
4. Set deterministic metadata (`SOURCE_DATE_EPOCH` from the source commit,
   normalized file ordering/mtimes, fixed OCI labels). Do not use wall-clock
   time as image content.
5. Build twice from separate clean directories and export OCI layouts without
   registry push. Compare platform manifest/config/layer digests.
6. Generate SPDX or CycloneDX SBOM, licence inventory, vulnerability report and
   SLSA-compatible provenance whose subject is the exact OCI digest.
7. Only after Product Owner approval, push that verified artifact to GHCR and
   compare the observed registry digest. A mismatch fails G3.

## Runtime lock schema semantics

The lock is a closed JSON object with a release identity and exactly three
closed image objects. Important invariants:

- `reference == repository + "@" + digest`;
- `display_tag == repository + ":" + version`;
- `digest` matches `sha256:[0-9a-f]{64}`;
- `platform.os == "linux"` and `platform.architecture == "amd64"`;
- byte counts are positive integers and are not labelled exact until measured;
- evidence paths are repository-relative and each has a SHA-256;
- probe command and expected fields are selected by logical ID, not arbitrary
  manifest strings at runtime;
- source commit equals the installer build commit.

The Installer stores the same lock under the PLwC app installation. The
Gateway verifies its schema and uses it for all three operations. Missing or
invalid lock means Safe Mode for those functions, never a fallback tag pull.

## Hardened probe contract

Every probe uses:

```text
docker run --rm --pull never --network none --read-only
  --cap-drop ALL --security-opt no-new-privileges
  --pids-limit 64 --memory 512m --cpus 1
  --user <image-specific-non-root-id> --tmpfs /tmp:rw,noexec,nosuid,size=64m
  <repository>@sha256:<digest> <fixed-probe>
```

Document Worker receives a newly created empty probe directory mounted at
`/work`; Node/Python need no host mount. The wrapper caps stdout/stderr and
time. PASS requires exit 0, expected output, no network, matching inspected
digest/platform and cleanup of the probe container.

## Pull and state algorithm

- Inventory is read-only and always runs before the UI decision.
- Exact local presence gives `present`; absence gives `download_required`.
- Consent `false` performs no process start and records `safe_mode`.
- Consent `true` pulls only absent exact refs, one at a time, with platform.
- Digest and platform are inspected after every pull and before every run.
- All three probes run even if the images were already local.
- The aggregate state is `ready` only for three `probe_passed` states.
- First failure stops subsequent network actions; already verified entries and
  the unattempted list are recorded. A new explicit attempt is idempotent.

No component performs `docker build` on an end-user computer. GHCR acquisition
is distribution of prebuilt, reviewed artifacts, not a local source build.
