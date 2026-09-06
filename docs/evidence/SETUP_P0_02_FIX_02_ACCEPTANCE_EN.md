# Windows Setup P0-02 Fix 02 Acceptance Evidence

Date: 2026-08-06

Scope: SETUP-P0-02-FIX-02 only. This pass integrates the accepted
BRIDGE-P0-02-FIX-01 Chat Bridge build into the Windows Setup payload, advances
the installer revision to `installer-r12`, performs a fresh Bridge and browser
extension source build, verifies the staged continuation protocol and component
identity, compiles the production Setup executable, and runs guarded local UI
acceptance.

Browser Store packaging or publication, clean-machine prerequisite vendor
installation, preserved-VM installation, and a live post-install ChatGPT
profile apply remain outside this host pass.

## Trigger

`installer-r11` completed installation successfully on the preserved Windows
VM, but it contained the earlier Chat Bridge payload. BRIDGE-P0-02-FIX-01 then
accepted the governed `profile_creation` continuation, execution-refusal
recovery, runtime-status follow-up, and aligned `0.2.0-rc19.dev19` component
identity. A new installer was required before that fix could be tested on the
VM.

## Outcome

SETUP-P0-02-FIX-02 passes automated source, staged-payload, production-build,
hash-linkage, and guarded local UI acceptance on this host.

The resulting `installer-r12` keeps the Gateway at `0.2.0-rc18.dev9` and binds
the common Chat Bridge release, Node Bridge, browser extension, and native
launcher to `0.2.0-rc19.dev19`. The builder compiled the Node Bridge and
extension from a fresh isolated source tree instead of consuming previous
working `dist` directories.

The staged extension contains `plwc_onboarding_continuation.v1`, the
`awaiting_user_confirmation` and `verify_active_profile` states, and the
Governor-versus-Describe recovery guard accepted in BRIDGE-P0-02-FIX-01.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Advance the installer without reusing r11 identity | PASS | Setup and all generated records use the distinct `installer-r12` revision and artifact name. The preserved VM installation remains the accepted r11 baseline. |
| Bind Setup defaults to the accepted Bridge | PASS | Node Bridge, browser extension, native launcher, Bridge directory, and generated config track use `0.2.0-rc19.dev19`. |
| Bind the component contract to dev19 | PASS | `components.json` product metadata, Chat Bridge component version, install destinations, native-manifest expectations, and browser-extension output path use dev19. |
| Build from current source | PASS | `build.ps1` ran without `-SkipNodeBuild`, performed isolated `npm ci`, compiled the Bridge with TypeScript, and built the extension with its production builder. |
| Reject stale staged identities | PASS | Independent scans found no Bridge `dev12` or `dev18` identity in the staged build identity, compiled Bridge, extension, or config. |
| Carry the onboarding fix | PASS | The staged compiled extension contains the versioned continuation protocol, both continuation states, and the `plwc_describe` substitution guard. Its accepted Bridge artifact hashes match BRIDGE-P0-02-FIX-01. |
| Link installer and payload hashes | PASS | Independent SHA-256 calculations equal the external build identity and every `SHA256SUMS.txt` record. |
| Preserve Setup behavior | PASS | The complete Setup suite passed 62 of 62 contracts, including the prior prerequisite, diagnostics, identity, size, workspace, and payload gates. |
| Verify localized guarded UI | PASS | English and German production smokes reached the localized Ready page and stopped before installation. |
| Verify explicit Bridge selection | PASS | The guarded English smoke selected `PLwC Chat Bridge`, retained all prior markers, reached Ready, and did not start installation. |

## Verification

PowerShell parser validation passed for `build.ps1`,
`installer-contract.Tests.ps1`, and `installer-ui-smoke.ps1`. The component
manifest parsed as JSON. A new source contract requires r12 and the complete
accepted dev19 identity across Setup and the component manifest.

The complete Setup suite was executed from `installer/windows`:

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Accepted result:

```text
Passed: 62 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
Duration: 383.12 seconds
```

The production installer was built from fresh Bridge and extension sources:

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
Duration: 515.6 seconds
```

Independent post-build checks printed:

```text
IDENTITY_HASH_LINKAGE_VERIFIED
PAYLOAD_COMPONENT_IDENTITY_VERIFIED
DIST_CHECKSUMS_VERIFIED
STAGED_BRIDGE_DEV19_VERIFIED
STAGED_ONBOARDING_FIX_AND_MANIFEST_VERIFIED
```

The final staged payload contains 3,503 files and 17,448,327 bytes, displayed
as 17 MiB by the existing ceiling-based Setup size contract.

Guarded production UI smokes were executed in English and German with the
diagnostic, build-identity, size-breakdown, and prerequisite-flow markers. Both
reached `Install` / `Installieren` and stopped before installation. A third
English smoke explicitly selected `PLwC Chat Bridge` and also reached Ready.

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r12.exe
Bytes  5,163,768
SHA256 50b1d5782aef81d6a41c776ecfca210883caa8d6eb21f0910affbeaf5534bc2e

PLwC-0.2.0-rc18.dev9-payload-manifest.json
Bytes  992,342
SHA256 539aa48d1340f451e3037b7ac05ef27544b935ce72591c8a9f5dd05bacfea14e

PLwC-0.2.0-rc18.dev9-installer-r12-build-identity.json
Bytes  1,249
SHA256 4b2b854e8e8c6d5222383777000a44388c5c888c939ec42b2422173cb525bac3
```

Build ID:

```text
plwc-windows-setup@0.2.0-rc18.dev9/installer-r12#sha256:50b1d5782aef81d6a41c776ecfca210883caa8d6eb21f0910affbeaf5534bc2e
```

Accepted staged Bridge records:

```text
chat-bridge/build-identity.json
SHA256 93a116cc44a59dd640b4a49f5dc73b975756a733bf4ab7a21df6c42e29f1016a

chat-bridge/bridge/dist/src/index.js
SHA256 33848b6a436db9be7ace2debe472e260db84e4684bb552fa0eb5039ea6cccb4e

chat-bridge/extension/manifest.json
SHA256 d8b6fe778de88515395334525ea27c60eeaa4bdcebd304468d58e35d0dfa83b7

chat-bridge/extension/background.js
SHA256 ae91c49b46fb4b0a888aedf15ed1ed582255ab620698a9210fa653c694560867

chat-bridge/extension/content.js
SHA256 ea6ed31ad03435b1fa24e38f36a042983f97c44df4b917c167114753bba73731

chat-bridge/native/bin/plwc-chat-bridge-launcher.exe
SHA256 6ff794e5073209f1251acda9e4811214db5d3378c734caf5824ddf4397802b8f
```

The native launcher was freshly compiled for this Setup build, so its binary
hash differs from the earlier Bridge acceptance artifact while its reported
build ID and all three component versions remain exactly dev19.

## Preserved-VM Acceptance Procedure

1. Preserve the current VM snapshot and keep the successful r11 installer and
   its logs as the baseline.
2. Verify the r12 Setup SHA-256 before launch.
3. Run r12 for the signed-in test user and select `PLwC Chat Bridge`.
4. Confirm the installed active path is
   `%APPDATA%\PLwC\app\chat-bridge-0.2.0-rc19.dev19` and that Native Messaging,
   autostart, and generated Bridge config point to that directory.
5. Open the extension Status view and verify common build, Node Bridge,
   Extension, and Launcher all report `0.2.0-rc19.dev19`, with eight of eight
   tools and no local error.
6. Start a fresh profile onboarding conversation and run
   `plan -> explicit user confirmation -> apply -> runtime status`.
7. Confirm the apply remains governed, the complete reviewed onboarding data
   is retained, no invalid Governor Describe substitution occurs, and the
   requested profile is active.
8. Retain screenshots plus Setup, Bridge, and Gateway diagnostic logs for the
   final VM acceptance record.

## Non-Final Diagnostic Notes

An initial complete Pester invocation used a 120-second command timeout, which
was too short for the payload build gate and produced no accepted result. The
authoritative rerun used a 600-second limit and completed all 62 tests in
383.12 seconds.

An initial compiled-extension marker check required one exact English guard
sentence that differed from the accepted source wording. The result was not
treated as a package failure. The source-accurate rerun verified the protocol,
both continuation states, the `plwc_describe` guard token, and all staged
manifest hashes.

## Implementation Boundary

- `installer/windows/PLwCSetup.iss` owns the r12 default revision, displayed
  component versions, versioned Bridge directory, and generated config track.
- `installer/windows/build.ps1` owns fresh staging, canonical identity checks,
  payload and EXE hash records, and this package's evidence attribution.
- `installer/windows/manifests/components.json` owns the planned dev19 install
  destinations and post-install expectations.
- `installer/windows/tests/installer-contract.Tests.ps1` owns the r12/dev19
  regression contract and complete staged-payload gate.
- `installer/windows/tests/installer-ui-smoke.ps1` owns the r12 guarded UI path.

## Outside This Package

- No Browser Store package, listing, account, publisher identity, or submission
  was created.
- No prerequisite vendor installer was executed as acceptance evidence.
- No preserved-VM installation or live ChatGPT profile write was performed on
  this host.
- No PLwC core, Gateway, Chat Bridge, extension, or launcher product source was
  changed in this integration package.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
