# G1 payload and ownership boundary - r27

Date: 2026-09-05

Status: **APPROVED**

## Installer EXE allowlist

The r27 EXE may contain only the already reviewed PLwC application payload plus
these new small control artifacts:

- the runtime-image JSON schema and exact release lock;
- the image manager and its tests/contract metadata needed at install time;
- bilingual installer strings and UI definitions;
- build identity, payload hashes, licences and public evidence references.

The EXE does **not** embed Docker images, OCI archives, a Docker registry token,
a GitHub PAT, Docker credentials, an unfiltered repository, a wheelhouse, build
caches, SBOM source databases or vulnerability scanner caches. Container layer
bytes are external downloads from the exact GHCR digest and only after consent.

## Runtime image allowlist

Exactly three PLwC-controlled `linux/amd64` images are allowed:

| ID | Repository | Runtime purpose |
| --- | --- | --- |
| `document_worker` | `ghcr.io/mhoedt-ai/plwc-document-worker` | governed document operations |
| `node_runner` | `ghcr.io/mhoedt-ai/plwc-node-runner` | Node sandbox |
| `python_runner` | `ghcr.io/mhoedt-ai/plwc-python-runner` | Python sandbox |

The release lock must bind every image by registry manifest digest. Any fourth
image, another owner/registry/platform, `latest`, tag-only reference or dynamic
image name fails the build and Installer validation.

Build inputs may include reviewed digest-pinned upstream bases, a fixed Debian
snapshot/package lock, the hash-locked Document Worker wheelhouse and repository
source at the recorded commit. Build inputs are not Installer payload.

## Write ownership

| Location/state | Owner | Upgrade | Normal uninstall |
| --- | --- | --- | --- |
| Installed runtime-image lock and schema | Installer | versioned replace after hash check | remove with app payload |
| Image acquisition reports under PLwC logs | Installer/User | preserve and append | preserve as diagnostic/user state unless explicitly selected |
| Per-image state under PLwC state | Installer/Runtime | atomically replace | preserve unless explicitly selected |
| GHCR image manifests/layers in Docker content store | Docker/shared | reuse by exact digest | do not delete |
| Friendly local tags | not trusted state | optional display only | do not delete automatically |
| Profiles and workspace | User | byte-preserve | preserve |
| Docker config/credentials/daemon settings | User/Docker | never mutate | never mutate |

Acquisition before the PLwC file transaction may add verified blobs to Docker's
store but cannot alter profile, workspace or client registrations. Cancellation
does not attempt broad Docker cleanup because content can be shared and Docker
already owns safe garbage collection.

## Privacy and secret denylist

Build contexts, EXE payload, OCI layers and release evidence must reject:

- real profiles, workspaces, diaries, Temp/Trashcan content or transcripts;
- `.env`, tokens, credentials, Docker `config.json`, SSH/GPG material, cookies
  or browser profiles;
- real `security.yaml`, machine-specific state, logs or crash dumps;
- absolute private user, drive, UNC or temporary paths;
- registry authentication headers or command lines containing secrets;
- repository `.git`, developer caches, virtual environments and local image
  exports.

Diagnostics may contain local paths on the affected user's own machine, but an
export must mark them sensitive and release evidence must redact them. stdout
and stderr are bounded and redacted before persistence.

## Network boundary

- Installer network access is limited to anonymous HTTPS pulls performed by
  Docker for locked `ghcr.io/mhoedt-ai/...@sha256:...` references.
- The manager performs no login and no direct GitHub API call.
- Probes and normal runtime use `--pull never --network none`.
- No runtime operation gains a network fallback if an image is missing.

Decision: the allowlist and denylist satisfy SR-005, SR-006, SR-009 and SR-011
at design level. Their enforcement is required by G2 tests and G3/G4 scans.
