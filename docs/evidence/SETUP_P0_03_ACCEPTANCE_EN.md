# Windows Setup P0-03 Acceptance Evidence

Date: 2026-08-05

Scope: SETUP-P0-03 only. This pass covers installer build identity, component
version binding, the setup executable SHA-256, runtime installation records,
payload metadata, production compilation, contract tests, and one guarded UI
smoke run on this host.

Size and runtime guidance (SETUP-P1-01), clean-machine installation testing
(SETUP-P0-04), final 1.0.0 versioning, and G5/G6 release acceptance remain
outside this pass.

## Outcome

SETUP-P0-03 passes on this host for source contracts, payload staging,
production compilation, generated artifact identity, hash linkage, and guarded
UI coverage.

The production build now emits a separate JSON identity record that binds the
exact setup EXE SHA-256 to the installer revision, payload manifest, Gateway,
Node Bridge, Browser Extension, Native Launcher, and this acceptance package.
The compiled installer calculates the hash again from the running `{srcexe}`
and writes the same build identity fields to the installation summary,
append-only diagnostic log, and generated `selection.ini`.

The guarded UI smoke intentionally stopped at the Ready page. It did not write
an installation to the host. Execution of the installed-file path on clean
Windows machines remains part of SETUP-P0-04; this pass verifies that the path
is present in the compiled production installer and is covered by contracts.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Record installer revision | PASS | The source and artifact name use `installer-r9`; payload and external identity records carry the same revision. |
| Record setup EXE SHA-256 | PASS | Runtime code hashes `{srcexe}` with `GetSHA256OfFile`; the external identity contains the independently verified production EXE hash. |
| Record Gateway version | PASS | `build.ps1` derives `0.2.0-rc18.dev9` from the Gateway manifest/project contract and passes it into the compiled installer. |
| Record Node Bridge version | PASS | The build validates and records canonical Node Bridge version `0.2.0-rc19.dev12`. |
| Record Browser Extension version | PASS | The build validates package, extension manifest, and shared Bridge identity before recording version `0.2.0-rc19.dev18`. |
| Record Native Launcher version | PASS | The build validates the shared Bridge identity and embedded launcher identity before recording version `0.2.0-rc19.dev18`. |
| Record installation mode | PASS | Runtime summary, diagnostic record, and `selection.ini` use `WizardSetupType(False)`. |
| Record selected components | PASS | The localized summary retains the readable component list; all three identity records include `WizardSelectedComponents(False)`, and `selection.ini` retains component booleans. |
| Write installation summary | PASS | `BuildInstallSummary` includes the complete identity before paths, prerequisite status, and component details. |
| Write diagnostic record | PASS | Successful post-install appends an `installation_completed` record with the complete identity; prerequisite exceptions use the same identity formatter. |
| Provide machine-readable installed identity | PASS | `[BuildIdentity]` in generated `selection.ini` contains build ID, revision, EXE hash, component versions, mode, and selected components. |
| Map an installed machine to build evidence | PASS | The runtime build ID is based on the exact EXE hash. The external JSON maps that hash to payload hash, component versions, package `SETUP-P0-03`, and this evidence path. |
| Compile and expose the revision in the UI | PASS | The production compile succeeded and guarded UI smoke printed `SETUP_P0_03_BUILD_IDENTITY_VISIBLE` before reaching Ready. |

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

Result:

```text
ValidateOnly complete. Payload staged and verified; ISCC was not invoked.
```

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Final result: all 57 installer contract tests passed.

```text
Passed: 57 Failed: 0 Skipped: 0 Pending: 0 Inconclusive: 0
```

```powershell
.\build.ps1 -SkipNodeBuild
```

Result:

```text
PLwC Windows installer build complete:
<REPOSITORY_ROOT>\installer\windows\dist\PLwC-Setup-0.2.0-rc18.dev9-installer-r9.exe

Build identity:
<REPOSITORY_ROOT>\installer\windows\dist\PLwC-0.2.0-rc18.dev9-installer-r9-build-identity.json
```

The identity linkage check independently recalculated the setup EXE and payload
manifest hashes, compared both values with the identity JSON, and confirmed both
entries in `SHA256SUMS.txt`.

```text
IDENTITY_HASH_LINKAGE_VERIFIED
```

```powershell
.\tests\installer-ui-smoke.ps1 `
  -Language english `
  -FixtureGuardsInstallation `
  -MaximumNextClicks 20 `
  -ExpectSetupP002Diagnostics `
  -ExpectSetupP003BuildIdentity
```

Result: the smoke reached the Ready page, stopped before installation, and
printed:

```text
SETUP_P0_03_BUILD_IDENTITY_VISIBLE
SETUP_P0_02_DIAGNOSTICS_VISIBLE
```

## Final Artifacts

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r9.exe
SHA256 b7a561cce8e5a659e15bb741e80f1579526657e4cb9fa2080eebbda4891ab9d6

PLwC-0.2.0-rc18.dev9-payload-manifest.json
SHA256 0d117a640290ae41ae3d63ae933709991820686eca7172aa04134fb41ef7b39b

PLwC-0.2.0-rc18.dev9-installer-r9-build-identity.json
SHA256 a3bff55f82197f5a64deebcaae119d694f3dc30559b1061ff5e2fcdb717e5b8d
```

The generated build ID is:

```text
plwc-windows-setup@0.2.0-rc18.dev9/installer-r9#sha256:b7a561cce8e5a659e15bb741e80f1579526657e4cb9fa2080eebbda4891ab9d6
```

## Non-Final Diagnostic Note

The first Pester run completed with 56 of 57 tests passing. The only failure was
an over-specific new regular expression that expected a closing quote directly
after `installer_revision=` even though the Inno preprocessor value follows in
the same string literal. The matcher was corrected without changing production
behavior. The complete final suite then passed 57 of 57 and is the accepted
result above.

## Implementation Boundary

- `installer/windows/build.ps1` derives and validates all component versions,
  emits installer compile definitions, and writes the external identity record.
- `installer/windows/PLwCSetup.iss` owns runtime EXE hashing and installed
  summary, diagnostic, and `selection.ini` identity records.
- `installer/windows/tests/installer-contract.Tests.ps1` owns source, staged
  payload, version-binding, and evidence-link contracts.
- `installer/windows/tests/installer-ui-smoke.ps1` owns the guarded visible
  installer-revision marker.
- `installer/windows/README.md` and `docs/WINDOWS_INSTALLER_GUIDE.md` document
  build outputs and installed support records.

## Non-P0-03 Items

- No product version was changed to 1.0.0.
- No PLwC Gateway or Chat Bridge product behavior was changed.
- No clean-machine G5 or SETUP-P0-04 acceptance claim was made.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
