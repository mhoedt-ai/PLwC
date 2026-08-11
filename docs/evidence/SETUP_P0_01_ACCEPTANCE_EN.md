# Windows Setup P0-01 Acceptance Evidence

Date: 2026-07-30

Scope: SETUP-P0-01 only. Prerequisite and VM diagnostics, reproducible Setup
identity, clean-machine acceptance, and final release testing remain outside
this acceptance pass.

## Outcome

SETUP-P0-01 passes.

New installation, upgrade, and repair use the same post-install path and the
same `EnsureWorkspaceStructureAt` implementation. The function creates only
these missing workspace directories:

```text
Tagebuch/
Temp/
Trashcan/
```

Every directory is checked with `DirExists` before `ForceDirectories` can be
called. Existing directories, files, custom workspace directories, hashes, and
timestamps are therefore left untouched.

The production Setup remains `PrivilegesRequired=lowest`. Only separately
selected prerequisite installers may request elevation. Workspace directories
are created by the signed-in user's non-elevated Setup process.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| New installation creates the standard structure | PASS | The isolated Setup fixture started with no workspace and created exactly `Tagebuch/`, `Temp/`, and `Trashcan/`. |
| Upgrade and repair use the same implementation | PASS | `CurStepChanged(ssPostInstall)` calls `SaveGeneratedFiles`, which calls the shared production `EnsureWorkspaceStructureAt(GetWorkspacePath(''))` exactly once on every Setup run. |
| Existing directories and contents are not overwritten | PASS | The fixture retained a journal file, a custom directory, a custom file, both SHA-256 values, and all protected timestamps. |
| First repair adds missing standard directories | PASS | The fixture removed empty `Temp/` and `Trashcan/` directories after the clean-install run. The next Setup run restored both without changing existing data. |
| Two later repairs make no data changes | PASS | Complete path, type, length, SHA-256, and UTC last-write snapshots after the first, second, and third repair were identical. |
| Setup does not create `Inbox/` | PASS | Static source guards reject `Inbox`; runtime checks confirmed it was absent after clean installation and repair. |
| Setup creates no additional workspace directories | PASS | The shared source contains exactly the three allowed directory literals. The clean-install workspace contained exactly those three directories. |
| Setup performs no cleanup or deletion | PASS | Static guards reject delete, remove, clear, and clean operations. The runtime fixture retained pre-existing custom data. |
| Directories belong to the signed-in user | PASS | The fixture Setup uses `PrivilegesRequired=lowest`; owner SIDs for all three created directories matched the current Windows user SID. |

## Shared Production Code

`installer/windows/assets/workspace-structure.iss` contains the production
implementation. It is included by both:

- `installer/windows/PLwCSetup.iss`
- `installer/windows/tests/workspace-structure-fixture.iss`

The fixture therefore compiles and executes the same Pascal procedure used by
the production Installer instead of duplicating its directory logic in
PowerShell.

## Verification Commands

Executed in `<REPOSITORY_ROOT>\installer\windows\tests`:

```powershell
.\installer-ui-smoke.ps1 -ExerciseWorkspaceStructure
```

Result:

```text
WORKSPACE_STRUCTURE_CLEAN_INSTALL_PASSED
WORKSPACE_STRUCTURE_FIRST_REPAIR_PASSED
WORKSPACE_STRUCTURE_REPEATED_REPAIR_PASSED
WORKSPACE_STRUCTURE_CURRENT_USER_OWNER_PASSED
```

The smoke compiled a minimal non-elevated Inno Setup executable, ran the shared
production code four times, and removed its isolated temporary artifacts.

Executed in the same directory:

```powershell
Invoke-Pester -Script .\installer-contract.Tests.ps1 -PassThru
```

Result: all 51 Installer source and payload contract tests passed. The suite
also completed a fresh `build.ps1 -ValidateOnly` staging run.

Executed in `<REPOSITORY_ROOT>\installer\windows`:

```powershell
.\build.ps1 -SkipNodeBuild
```

Result: the complete production Inno Setup source compiled successfully:

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r8.exe
SHA256 FD891F5D2E596EC552611B5149EEB579EA6142DAB5B3E22A8B9F5E56B9F546E1
```

`git diff --check` passed with line-ending conversion warnings only.

## Implementation Boundary

- `assets/workspace-structure.iss` owns the exact standard directory list and
  idempotent creation behavior.
- `PLwCSetup.iss` invokes the shared function from the common post-install
  generated-file path.
- `tests/workspace-structure-fixture.iss` provides an isolated, non-elevated
  executable host for the production function.
- `tests/installer-ui-smoke.ps1` owns runtime filesystem, idempotence, and
  ownership verification.
- `tests/installer-contract.Tests.ps1` owns static and dynamic regression
  gates.

## Non-P0-01 Items

- No prerequisite detection or acquisition behavior was changed.
- No application component selection or payload content was changed.
- No clean-machine or upgrade VM acceptance was claimed.
- No 1.0.0 version alignment was performed.
