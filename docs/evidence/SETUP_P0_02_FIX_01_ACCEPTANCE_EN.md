# Windows Setup P0-02 Fix 01 Acceptance Evidence

Date: 2026-08-06

Scope: SETUP-P0-02-FIX-01 only. This pass covers prerequisite detection
locking, stable prerequisite selection, continuous batch progress, bounded
Python and Node.js probes, elevated child-installer launch reliability,
localized error classification, installer contracts, production compilation,
and guarded English and German UI smoke coverage on this host.

Browser Store product work, Chat Bridge response routing, clean-machine
installation acceptance, third-party prerequisite installation on a preserved
VM, and final 1.0.0 release acceptance remain outside this pass.

## Outcome

SETUP-P0-02-FIX-01 passes its automated and guarded host acceptance. The main
setup remains a per-user process because PLwC installs below the current user's
application-data directory and writes HKCU state. Third-party installers that
need machine-level access continue to request elevation individually.

The Node.js launch failure with exit code 3 was traced to passing the 32-bit
process-only `{sysnative}` alias through the elevated ShellExecute handoff.
Node.js now launches the verified MSI through `{sys}\msiexec.exe`. Setup also
distinguishes UAC cancellation from executable-path resolution failures in its
localized failure details.

Prerequisite detection now locks the current action page in place, including
the choices and Back/Next navigation. Selected items are retained as a stable
batch plan. The progress page remains visible through downloads, elevated
child installers, and the final re-probe instead of returning to an apparently
empty selection page between operations.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Preserve the per-user setup identity | PASS | `PrivilegesRequired=lowest` remains in force; only verified third-party child installers request elevation. This avoids installing HKCU/user-data state under a different administrator profile. |
| Launch Node.js MSI across the UAC boundary | PASS | The Node.js path uses `{sys}\msiexec.exe`; source contracts reject `{sysnative}\msiexec.exe`. |
| Explain launch-path failures separately | PASS | Exit codes 2 and 3 receive path-resolution guidance, while UAC cancellation is classified separately. |
| Prevent interaction during prerequisite detection | PASS | The prerequisite list, official-site buttons, recheck button, Back, and Next are disabled while detection is active. |
| Keep detection on the current page | PASS | Detection updates the current report/status controls in place and does not reveal a different wizard page. |
| Prevent reentrant page refreshes | PASS | `PrerequisiteOperationBusy` suppresses `CurPageChanged` refresh work during active checks and batches. |
| Bound external runtime probes | PASS | Python version probes use a 5-second timeout, Python module probes use 30 seconds, and Node.js version probes use 5 seconds. |
| Preserve the user's selected plan | PASS | Selected prerequisite values are not cleared before execution; unresolved selections are restored after failure. |
| Keep one continuous batch progress surface | PASS | One prerequisite batch spans download, preparation/child installation, and final detection before the action page is restored. |
| Re-probe before continuing | PASS | The selected batch performs a final prerequisite check and the normal selected-component gate remains authoritative. |
| Verify normal English and German flows | PASS | Both guarded production UI smokes reached the localized Ready page and stopped before PLwC installation. |
| Verify a guarded download batch | PASS | The local fixture verified its SHA-256 download, prepared the guarded prerequisite path, completed final detection, and printed `SETUP_P0_02_FIX_01_BATCH_STABLE`. |
| Preserve earlier diagnostics, identity, and size guidance | PASS | Production smokes retained the SETUP-P0-02 diagnostics, SETUP-P0-03 build identity, and SETUP-P1-01 size markers. |

## Verification Commands

PowerShell parser validation covered `build.ps1`,
`installer-contract.Tests.ps1`, and `installer-ui-smoke.ps1`.

```text
POWERSHELL_SYNTAX_OK
```

The production source contract suite was executed with:

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Final result:

```text
Passed: 61 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
```

Production staging and compilation were executed with:

```powershell
.\build.ps1 -SkipNodeBuild
```

Result: the staged payload and final `installer-r11` executable compiled
successfully. Independent identity and payload checks printed:

```text
IDENTITY_HASH_LINKAGE_VERIFIED
PAYLOAD_SIZE_LINKAGE_VERIFIED
```

The English and German production UI smokes used the guarded installation
fixture with all prior setup markers and `-ExpectSetupP002Fix01Flow`. Both
reached the localized Ready page without starting installation and printed:

```text
SETUP_P0_03_BUILD_IDENTITY_VISIBLE
SETUP_P0_02_FIX_01_CHECK_LOCK_OBSERVED
SETUP_P0_02_DIAGNOSTICS_VISIBLE
SETUP_P1_01_SIZE_BREAKDOWN_VISIBLE
SETUP_P0_02_FIX_01_FAST_CHECK_COMPLETED
```

The focused local-download fixture selected the Gateway prerequisite plan,
served a pinned test asset from loopback, and exercised the guarded batch path.
It printed:

```text
SETUP_P0_02_FIX_01_CHECK_LOCK_OBSERVED
SETUP_P0_02_FIX_01_BATCH_STABLE
SETUP_P0_02_FIX_01_FAST_CHECK_COMPLETED
Installer UI smoke completed without starting installation.
```

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r11.exe
Bytes  5160455
SHA256 ecd175466ebd46eba63d0f7c286b0819480acdbb5689598987179367ecce60b4

PLwC-0.2.0-rc18.dev9-payload-manifest.json
Bytes  992342
SHA256 11c988d5bccf51237b6f19a8034219f27b8cd7065c7c84e7e6303bc7b20f02c6

PLwC-0.2.0-rc18.dev9-installer-r11-build-identity.json
Bytes  1249
SHA256 3c0dcf9ce18031b2ba37a3f92b86d1d0cf4d2ab1a24e06ad3d2044061ceac754
```

The staged payload contains 17,427,252 bytes (17 MiB). The generated build ID
is:

```text
plwc-windows-setup@0.2.0-rc18.dev9/installer-r11#sha256:ecd175466ebd46eba63d0f7c286b0819480acdbb5689598987179367ecce60b4
```

## Non-Final Diagnostic Notes

An early UI implementation used a separate detection progress page. Guarded UI
testing exposed a reentrant `CurPageChanged` loop and then a skipped action
page; both were corrected by locking and updating the current page in place.

One initial Pester invocation exceeded its command timeout, and a later
non-final run found two stale regular-expression expectations. Neither run was
accepted. The expectations were corrected and the complete final suite passed
61 of 61 tests.

The first focused batch-fixture attempt read its log before the final re-probe
could finish. Another harness check treated enabled UI Automation child items
as proof that their disabled parent list was interactive. The fixture now waits
for the batch-finished marker and checks the actual list container. The accepted
focused run passed.

## Implementation Boundary

- `installer/windows/PLwCSetup.iss` owns prerequisite detection, UI locking,
  stable batch state, child elevation, bounded probes, and failure guidance.
- `installer/windows/tests/installer-contract.Tests.ps1` owns static source and
  build-gate contracts for the fix.
- `installer/windows/tests/installer-ui-smoke.ps1` owns guarded visible lock,
  stable-batch, localization, and no-install smoke checks.
- `installer/windows/build.ps1` binds `installer-r11` to this acceptance record.
- Installer operator/user documentation records the per-user elevation model
  and continuous prerequisite flow.
- Governing setup plans record this fix as a prerequisite for the 1.0.0 Store
  delivery track.

## Non-Fix Items

- No Browser Store package, listing, account, draft item, or submission was
  created.
- No Chat Bridge, Browser Extension, or Native Launcher product code was
  changed.
- No prerequisite vendor installer was executed as acceptance evidence.
- No clean-Windows or preserved-VM acceptance claim was made.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
