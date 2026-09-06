# Windows Setup P0-02 Fix 03 Acceptance Evidence

Date: 2026-08-07

Scope: SETUP-P0-02-FIX-03 only. This pass integrates the accepted
BRIDGE-P0-02-FIX-02 Chat Bridge build into the Windows Setup payload, advances
the installer revision to `installer-r13`, replaces an installed dev19 Bridge
process during upgrade, binds detached startup health checks to the canonical
dev20 build identity, compiles the production Setup executable, and runs
guarded local acceptance.

Browser Store packaging or publication, the end-of-install introduction,
restart recommendation UX, prerequisite vendor installation, and preserved-VM
installation remain outside this package.

## Trigger

The accepted Bridge source and browser extension identify as
`plwc-chat-bridge@0.2.0-rc19.dev20`, while `installer-r12` still deploys dev19.
The extension correctly rejected a running dev19 Node Bridge because the common
build identity no longer matched. Setup therefore required a new payload and a
stronger upgrade path before dev20 could be accepted on the preserved VM.

The original autostart integration stopped only the PID recorded in
`%APPDATA%\PLwC\state\chat-bridge\bridge.pid`. A missing or stale PID file could
leave dev19 listening on port 3007. The detached launcher health check also
accepted any healthy eight-tool Bridge, so a surviving dev19 process could be
mistaken for the newly installed dev20 process.

## Outcome

SETUP-P0-02-FIX-03 passes source contracts, staged-payload checks, production
build, hash linkage, and guarded local UI acceptance on this host.

The resulting `installer-r13` keeps the Gateway at `0.2.0-rc18.dev9` and binds
the common Chat Bridge release, Node Bridge, browser extension, and native
launcher to `0.2.0-rc19.dev20`. Setup installs the Bridge under
`chat-bridge-0.2.0-rc19.dev20`.

During `-StartNow`, the autostart integration now enumerates only processes
whose command line contains the exact current or previously registered PLwC
Bridge entry path, stops every such owned process, and removes the stale PID
file. The detached launcher loads `build-identity.json` and passes its `buildId`
to `healthcheck.mjs` through `--expected-build-id`. A healthy dev19 Bridge can
therefore no longer satisfy the dev20 startup check.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Advance the installer identity | PASS | Setup, artifact names, generated records, and UI use `installer-r13`. |
| Bind Setup and the component contract to dev20 | PASS | Node Bridge, browser extension, native launcher, versioned Bridge directory, generated config track, component destinations, and post-install expectations use `0.2.0-rc19.dev20`. |
| Build from current source | PASS | The final build ran without `-SkipNodeBuild`, performed isolated `npm ci`, compiled the Bridge with TypeScript, and built the extension with its production builder. |
| Carry BRIDGE-P0-02-FIX-02 | PASS | The staged extension contains `composer-rejected-insertion`, `plwc_tool_call_correction.v1`, `invalid_onboarding_describe_filter`, and the complete-result copy fallback. |
| Replace the prior Bridge process | PASS | The installed autostart script enumerates exact current and previous Bridge entry paths even when the PID file is absent or stale. |
| Reject a stale healthy Bridge | PASS | The staged detached start script reads the canonical Bridge build identity and supplies `--expected-build-id` to every readiness probe. |
| Link installer and payload hashes | PASS | Independent SHA-256 calculations match the final external build identity and all `SHA256SUMS.txt` records. |
| Preserve Setup behavior | PASS | The complete Setup suite passed 62 of 62 contracts, including prerequisite, diagnostics, identity, size, workspace, payload, and new upgrade gates. |
| Verify localized guarded UI | PASS | English and German production smokes reached `Install` / `Installieren` and stopped before installation. |
| Verify explicit Bridge selection | PASS | A guarded English smoke selected `PLwC Chat Bridge`, displayed the dev20 target directory, reached Ready, and did not start installation. |

## Verification

Before implementation, the complete Setup suite passed 61 of 62 contracts.
The sole failure was the expected hard-coded dev19 identity after the canonical
Bridge source had advanced to dev20. All other Setup and staging contracts were
green.

PowerShell parser validation passed for the build, contract, UI smoke,
autostart, and detached-start scripts. The component manifest parsed as JSON.
No r12, dev19, or FIX-02 package metadata remains in the r13 Setup source,
component manifest, build script, or current contracts.

The complete Setup suite was executed from `installer/windows`:

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Accepted result:

```text
Passed: 62 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
Duration: 424.8 seconds
```

The final production installer was built after the contract suite, because the
suite's `ValidateOnly` gate intentionally resets generated `dist` output:

```powershell
.\build.ps1
```

Accepted result:

```text
Node Bridge npm ci and TypeScript build: passed
Browser extension npm ci and production build: passed
Production Bridge dependency staging: passed
Verified MCPB inclusion: passed
Payload validation and Inno Setup compilation: passed
Duration: 610.9 seconds
```

Independent post-build checks verified:

```text
INSTALLER_R13_IDENTITY_HASH_LINKAGE_VERIFIED
PAYLOAD_COMPONENT_DEV20_IDENTITY_VERIFIED
DIST_CHECKSUMS_VERIFIED
STAGED_POWERSHELL_SYNTAX_VERIFIED
STAGED_PREVIOUS_PROCESS_REPLACEMENT_VERIFIED
STAGED_EXPECTED_BUILD_HEALTHCHECK_VERIFIED
STAGED_BRIDGE_FIX_MARKERS_VERIFIED
```

The final payload manifest covers 3,503 payload files and 17,476,134 bytes,
displayed as 17 MiB by the existing Setup size contract. The manifest file
itself is intentionally outside its own file and byte totals.

Guarded production UI smokes were executed in English and German with the
diagnostic, build-identity, size-breakdown, and prerequisite-flow markers. Both
reached Ready. A separate English smoke explicitly selected `PLwC Chat Bridge`,
showed `chat-bridge-0.2.0-rc19.dev20`, and reached Ready. Every accepted smoke
stopped before installation.

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r13.exe
Bytes  5,167,337
SHA256 a76bed58512574fedb8f8fe918107d4cd626b4899b29d3c33d78e28cb42acc20

PLwC-0.2.0-rc18.dev9-payload-manifest.json
Bytes  992,342
SHA256 562c12081b4e1a96385f100fd1a260909266b462d55d9b5095d9f3bd3c2326da

PLwC-0.2.0-rc18.dev9-installer-r13-build-identity.json
Bytes  1,249
SHA256 53033741c4dd6f34aafd5c3f4a0798872dd2951d991d2815e965ff8466c51999
```

Build ID:

```text
plwc-windows-setup@0.2.0-rc18.dev9/installer-r13#sha256:a76bed58512574fedb8f8fe918107d4cd626b4899b29d3c33d78e28cb42acc20
```

Accepted staged Bridge records:

```text
chat-bridge/build-identity.json
SHA256 b364902839a88ffc71f6ba6c4e44a2ef897a7a56bf421d69f4aef773a9dda9c1

chat-bridge/bridge/dist/src/index.js
SHA256 33848b6a436db9be7ace2debe472e260db84e4684bb552fa0eb5039ea6cccb4e

chat-bridge/extension/manifest.json
SHA256 f1740376b7c17eca51e5c35b41746976c7df6e1d147f6f841771cc4de76b583b

chat-bridge/extension/background.js
SHA256 889f8e39d2fda87dd59d0f3cce6970468285787b298c9da5f7632637ec502c50

chat-bridge/extension/content.js
SHA256 0e84f14204878acaac2f44a6ac9d9dd485e0add83ddfc830a610437fb0ab3a9d

chat-bridge/native/bin/plwc-chat-bridge-launcher.exe
SHA256 e3c29c0cc1b313ad9459178ad95d2503294faefb7aebcf098730b3316c09bcb5

chat-bridge/scripts/start-windows.ps1
SHA256 1c47baf8f97b8e24ab64f8714c2fd052f97e58efbc1e87687fc78a55ec11aa23

chat-bridge/scripts/install-autostart-windows.ps1
SHA256 28d2b193c26bc693ee2bb77cdee7f509b5de8c018d14ceec955433462f128518
```

The freshly compiled native launcher reports
`plwc-chat-bridge@0.2.0-rc19.dev20` and dev20 for all three Bridge components.

## Preserved-VM Acceptance Procedure

1. Preserve the current VM snapshot and keep the existing dev19 installation
   and its logs as the upgrade baseline.
2. Verify the r13 Setup SHA-256 before launch.
3. Run r13 for the signed-in test user and select `PLwC Chat Bridge`. Do not
   manually stop the old Bridge or start the scheduled task.
4. Confirm the installed active path and
   `%APPDATA%\PLwC\config\chat-bridge-launcher.json` use
   `chat-bridge-0.2.0-rc19.dev20`.
5. Confirm the `PLwC Chat Bridge` scheduled task points to the dev20 start
   script and no running process command line references the dev19 Bridge
   `dist\src\index.js`.
6. Open the extension Status view and verify common build, Node Bridge,
   Extension, and Launcher all report `0.2.0-rc19.dev20`, with eight of eight
   tools and no local error.
7. Run the first-run status and onboarding flow. Confirm the corrected tool
   call stays in the composer, remains editable until submission, and the
   complete result is available when automatic submission is unavailable.
8. Retain screenshots plus Setup, Bridge, and Gateway diagnostic logs for the
   preserved-VM acceptance record.

## Non-Final Diagnostic Notes

The first full r13 build was intentionally followed by the complete Pester
suite. Its `ValidateOnly` build gate reset `dist`, so that non-final executable
was discarded and a second full production build created the final artifact
listed above.

The two complete Inno Setup builds differed by three bytes and therefore did
not produce the same executable hash. The final external build identity and
`SHA256SUMS.txt` both correctly bind the final executable. This package does not
claim bit-for-bit reproducibility of separately compiled Inno executables.

An exploratory explicit-Bridge UI run encountered transient automation timing:
one run advanced while Inno path validation dialogs were still being dismissed,
and another observed the persistent lock explanation just after `Next` had been
re-enabled. A diagnostic rerun without that timing-sensitive text assertion
showed all complete absolute paths, including the dev20 Bridge directory, and
reached Ready. The lock/unlock contract and both normal localized smokes passed.

## Implementation Boundary

- `installer/windows/PLwCSetup.iss` owns the r13 revision, displayed component
  versions, versioned Bridge directory, and generated config track.
- `installer/windows/build.ps1` owns fresh staging, canonical identity checks,
  payload and EXE hash records, and this package's evidence attribution.
- `installer/windows/manifests/components.json` owns the planned dev20 install
  destinations and post-install expectations.
- `integrations/plwc-chat-bridge/scripts/install-autostart-windows.ps1` owns
  exact current/previous installed Bridge process replacement.
- `integrations/plwc-chat-bridge/scripts/start-windows.ps1` owns build-bound
  detached startup readiness checks.
- `installer/windows/tests/installer-contract.Tests.ps1` owns the r13/dev20
  and upgrade regression contracts.
- `installer/windows/tests/installer-ui-smoke.ps1` owns the r13 guarded UI path.

## Outside This Package

- No Browser Store package, listing, account, publisher identity, or submission
  was created.
- No end-of-install introduction document or restart recommendation was added.
- No prerequisite vendor installer was executed as acceptance evidence.
- No preserved-VM installation or live ChatGPT profile write was performed on
  this host.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
