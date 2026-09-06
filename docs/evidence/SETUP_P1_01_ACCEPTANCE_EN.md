# Windows Setup P1-01 Acceptance Evidence

Date: 2026-08-05

Scope: SETUP-P1-01 only, plus the explicitly approved 1.0.0 Browser Store
distribution roadmap documentation. This pass covers installer download and
installed-storage guidance, build-derived PLwC payload sizing, explicit unknown
variable sizes, English and German UI contracts, production compilation,
contract tests, and one guarded UI smoke run on this host.

Browser Store product work, Bridge Store packages, Store account creation or
submission, prerequisite downloads, clean-machine installation testing
(SETUP-P0-04), and final 1.0.0 release acceptance remain outside this pass.

## Outcome

SETUP-P1-01 passes on this host. The installer now presents the staged PLwC
payload, Python, Node.js, Docker Desktop, WSL runtime/images, first-use model and
cache downloads, and selected known downloads as separate size classes.

The PLwC payload value is calculated from the verified staged files during the
build and compiled into the installer. Downloads whose size is not available at
setup time are shown as `unknown` or `unbekannt`; they are not represented as
null or zero and are excluded from the selected known-download total.

The 1.0.0 planning documents also record the required serial Store delivery
track: `STORE-G0-01`, `BRIDGE-P0-03` with renewed H2 acceptance,
`SETUP-P0-05`, `STORE-P0-02`, and then `SETUP-P0-04`. The plan preserves browser
installation consent and the boundary between a Store-delivered extension and
the separately installed native launcher.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Show the PLwC application payload separately | PASS | The production stage contains 17,427,252 bytes; the generated manifest records 17 MiB and the build passes that value into `PLwCSetup.iss`. |
| Show Python separately | PASS | The installer lists the Python download and installed-storage estimate independently. |
| Show Node.js separately | PASS | The installer lists the Node.js download and installed-storage estimate independently. |
| Show Docker Desktop separately | PASS | The installer lists the Docker Desktop download and its multi-GB installed-storage floor independently. |
| Represent WSL runtime and image downloads honestly | PASS | WSL runtime/image downloads have their own row and display `unknown`/`unbekannt`, with explanatory text. |
| Represent variable first-use downloads honestly | PASS | The default embedding-model range is shown separately and additional model/cache downloads display `unknown`/`unbekannt`. |
| Avoid null or zero placeholders for unknown sizes | PASS | Source contracts reject null and `0 MB`/`0 GB` representations for variable WSL, first-use, and later selected downloads. |
| Keep known and unknown totals distinct | PASS | The selected known-download total includes only known prerequisite estimates; variable later downloads remain a separate unknown class. |
| Provide English and German installer guidance | PASS | Localized size labels, explanatory text, and explicit unknown values are covered by source contracts. |
| Bind the displayed PLwC payload size to the staged payload | PASS | The manifest byte total was independently recalculated from the staged files and matched exactly; the MiB value uses a ceiling conversion. |
| Verify the compiled UI | PASS | Guarded UI smoke printed `SETUP_P1_01_SIZE_BREAKDOWN_VISIBLE` and stopped on the Ready page before installation. |
| Preserve earlier setup diagnostics and identity | PASS | The same smoke run printed `SETUP_P0_02_DIAGNOSTICS_VISIBLE` and `SETUP_P0_03_BUILD_IDENTITY_VISIBLE`. |
| Record the Browser Store delivery track for 1.0.0 | PASS | Both governing planning documents contain the serial Store gate, Bridge reissue, Setup integration, controlled publication, and clean-Windows acceptance order. |

## Verification Commands

Executed in `<REPOSITORY_ROOT>\installer\windows`:

```powershell
$errors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path 'build.ps1'), [ref] $null, [ref] $errors)

$errors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path 'tests\installer-contract.Tests.ps1'), [ref] $null, [ref] $errors)

$errors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path 'tests\installer-ui-smoke.ps1'), [ref] $null, [ref] $errors)
```

Result: all three PowerShell syntax checks passed.

```powershell
.\build.ps1 -ValidateOnly -SkipNodeBuild
```

Result: the final staging run passed. Independent verification produced:

```text
ManifestBytes 17427252
ActualBytes   17427252
ManifestMiB   17
ActualMiB     17
Revision      installer-r10
Evidence      SETUP-P1-01
PAYLOAD_SIZE_LINKAGE_VERIFIED
```

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Final result: all 59 installer contract tests passed.

```text
Passed: 59 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
```

```powershell
.\build.ps1 -SkipNodeBuild
```

Result: the production installer and external build identity compiled
successfully as `installer-r10`.

The final linkage check independently recalculated the setup EXE and payload
manifest hashes, matched both values against the build identity JSON, and found
both entries in `SHA256SUMS.txt`.

```text
IDENTITY_HASH_LINKAGE_VERIFIED
```

```powershell
.\tests\installer-ui-smoke.ps1 `
  -Language english `
  -FixtureGuardsInstallation `
  -MaximumNextClicks 20 `
  -ExpectSetupP002Diagnostics `
  -ExpectSetupP003BuildIdentity `
  -ExpectSetupP101SizeBreakdown
```

Result: the smoke reached the Ready page, stopped before installation, and
printed:

```text
SETUP_P0_03_BUILD_IDENTITY_VISIBLE
SETUP_P0_02_DIAGNOSTICS_VISIBLE
SETUP_P1_01_SIZE_BREAKDOWN_VISIBLE
```

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r10.exe
Bytes  5159597
SHA256 6dbb6e027293c27801de21c8cc8ba3e020184de5b86b6f121bc3ea93d545a5ce

PLwC-0.2.0-rc18.dev9-payload-manifest.json
Bytes  992328
SHA256 0833c94241271384facfb92307dfc4a694983a2c96f6ee4f5cbe4bd1ff5289bc

PLwC-0.2.0-rc18.dev9-installer-r10-build-identity.json
Bytes  1235
SHA256 dc5e7342d135136d2ae3b67832147edd97f26339a6c574baa529186404ed9c76
```

The generated build ID is:

```text
plwc-windows-setup@0.2.0-rc18.dev9/installer-r10#sha256:6dbb6e027293c27801de21c8cc8ba3e020184de5b86b6f121bc3ea93d545a5ce
```

## Non-Final Diagnostic Note

The first validation-only staging attempt failed while summing sizes because
the local PowerShell version did not expose ordered-dictionary keys through
`Measure-Object -Property size`. The calculation was changed to read each
dictionary entry explicitly. A focused calculation check and the complete
validation-only staging run then passed; the successful full run is the
accepted result above.

## Implementation Boundary

- `installer/windows/build.ps1` calculates and validates staged payload bytes
  and MiB, passes the compiled size definition, and emits evidence-bound build
  metadata.
- `installer/windows/assets/prerequisite-sizes.iss` owns versioned prerequisite
  estimates and permits the build-derived payload value.
- `installer/windows/PLwCSetup.iss` owns localized rendering and separation of
  known versus unknown size classes.
- `installer/windows/tests/installer-contract.Tests.ps1` owns source, payload,
  localization, evidence, and Store-roadmap contracts.
- `installer/windows/tests/installer-ui-smoke.ps1` owns the guarded visible
  size-breakdown marker.
- `installer/windows/README.md` and `docs/WINDOWS_INSTALLER_GUIDE.md` document
  the operator and user-facing size model.
- `docs/ARBEITSAUFTRAG_PLWC_BRIDGE_SETUP.md` and
  `docs/WINDOWS_INSTALLER_PLAN.md` own the approved 1.0.0 Store roadmap.

## Non-P1-01 Items

- No Browser Store package, listing, account, draft item, or submission was
  created.
- No Chat Bridge, Browser Extension, or Native Launcher product code was
  changed.
- No browser consent was bypassed and no extension was installed by Setup.
- No prerequisite or model download was executed as acceptance evidence.
- No clean-machine G5 or SETUP-P0-04 acceptance claim was made.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
