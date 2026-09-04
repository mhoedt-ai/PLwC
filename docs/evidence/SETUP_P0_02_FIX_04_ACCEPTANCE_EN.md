# Windows Setup P0-02 Fix 04 Acceptance Evidence

Date: 2026-08-08

Scope: PLWC-P1-02-FIX-01 and its Windows Setup integration
SETUP-P0-02-FIX-04. This package prevents optional Docker readiness timeouts
from aborting first-run onboarding, advances the Gateway to
`0.2.0-rc18.dev10`, advances Windows Setup to `installer-r14`, and preserves
the accepted Chat Bridge `0.2.0-rc19.dev20` identity.

## Trigger

On the preserved Windows VM, `plwc_status(scope="first_run")` raised a tool
execution error after `docker.exe info` exceeded its five-second timeout.
Docker is optional and the Windows installer contract explicitly requires a
visible Safe Mode path. The failed probe therefore must not block governed
profile creation.

## Outcome

`DockerSandboxAdapter.status()` now catches daemon and sandbox-image probe
timeouts and returns structured Safe Mode state. A daemon timeout records that
the Docker CLI is present while the daemon is unavailable. The first-run
status remains callable and continues to expose the governed
`profile_creation` route. Node-image readiness timeouts also remain diagnostic
and do not escape the status boundary.

The resulting Setup installs the Gateway under
`gateway-0.2.0-rc18.dev10`. The Node Bridge, browser extension, and native
launcher remain on `0.2.0-rc19.dev20` and the Bridge directory remains
`chat-bridge-0.2.0-rc19.dev20`.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Daemon timeout enters Safe Mode | PASS | Regression test raises `subprocess.TimeoutExpired` from `docker info`; the adapter returns without raising and reports CLI present/daemon unavailable. |
| Image timeout enters Safe Mode | PASS | Regression test raises during sandbox-image inspection and receives structured Safe Mode state. |
| First-run onboarding continues | PASS | `plwc_status(scope="first_run")` returns onboarding state and a `profile_creation` next action after the simulated daemon timeout. |
| Preserve public error policy | PASS | Existing error-governance and sandbox acceptance contracts pass; true policy denials remain separate. |
| Bind Gateway dev10 | PASS | Python metadata, MCPB manifest, component manifest, staged Gateway, payload manifest, and external build identity report dev10. |
| Preserve Bridge dev20 | PASS | Bridge workspace and Setup component identities remain dev20 for Node, extension, and launcher. |
| Bind Setup r14 | PASS | Source, payload manifest, external build identity, UI, and artifact name report `installer-r14`. |
| Verify localized UI | PASS | English and German production smokes reached the localized Ready page and stopped before installation. |

## Verification

Gateway suite:

```text
45 passed, 6 skipped
```

The skipped checks require Docker-backed or symlink-capable system acceptance
conditions and are not unit failures.

Chat Bridge workspace:

```text
Node Bridge:        23 passed
Browser extension: 140 passed
```

Windows Setup contract suite:

```text
Passed: 62 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
```

The complete contract suite performed a fresh isolated Node build, staged the
Gateway and extension, included the verified dev10 MCPB, validated privacy and
path boundaries, and checked the complete payload manifest.

Guarded production UI smokes passed in English and German with explicit Chat
Bridge selection. Both reached page 10 and stopped on `Install` /
`Installieren` before installation.

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev10-installer-r14.exe
Bytes  5,178,624
SHA256 1817eb1efd2c5616d239fa83321bb8de4de35e133d8d960568b20ac96e6ef54f

PLwC-0.2.0-rc18.dev10-payload-manifest.json
SHA256 71cbba7b58e5030d68580f58147abfdfdc9bb89dee98e263eacf8c31fa27f79a

PLwC-0.2.0-rc18.dev10-installer-r14-build-identity.json

plwc-gateway-0.2.0-rc18.dev10.mcpb
Bytes  549,021
SHA256 8b846c9bae5048c538a4c6082154ab18427690a027dfb0eb3fc654a070ef53ad
```

Build ID:

```text
plwc-windows-setup@0.2.0-rc18.dev10/installer-r14#sha256:1817eb1efd2c5616d239fa83321bb8de4de35e133d8d960568b20ac96e6ef54f
```

The payload contains 3,503 files and 17,489,315 bytes, displayed as 17 MiB by
the existing Setup size contract. The staged Gateway contains both the daemon
and sandbox-image timeout guards.

## Preserved-VM Acceptance Procedure

1. Keep the current VM state with Bridge dev20 and the incomplete `default`
   profile as the baseline.
2. Verify the r14 Setup SHA-256 before launch.
3. Install r14 with PLwC Chat Bridge selected. Do not manually start Docker.
4. Confirm the Gateway path uses `gateway-0.2.0-rc18.dev10` and Bridge,
   extension, and launcher still report dev20 with `8 / 8` tools.
5. Call `plwc_status(scope="first_run")` while Docker Desktop is stopped or
   unresponsive. The call must return Safe Mode and onboarding guidance, not a
   tool execution error.
6. Complete `profile_creation` plan, explicit confirmation, apply, and runtime
   verification.
7. Retain screenshots plus Setup, Bridge, and Gateway diagnostic logs.

## Preserved-VM Result

The exact r14 path completed the preserved-VM end-user run. Gateway dev10
reported eight of eight tools, the governed `default` profile became valid and
active, the Bridge persona toggle propagated through shared configuration, and
a full profile compile completed with an intact persona layer and complete
chunk reconstruction.

The same run also accepted a confirmed Reflection write, rejected a premature
Reflection-to-Memory promotion for insufficient independent evidence, wrote a
confirmed diary entry, rejected permanent workspace deletion, and completed
the explicitly confirmed move to `Trashcan/`.

The screenshots and the complete execution record are retained in
[`SETUP_P0_02_FIX_04_VM_ACCEPTANCE_EN.md`](SETUP_P0_02_FIX_04_VM_ACCEPTANCE_EN.md).

## Final Disposition

Local source, package, build, hash, guarded UI, and preserved-VM end-to-end
acceptance pass. The manual Windows system gate for r14 is closed.
