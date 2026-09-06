# Windows Setup P0-02 Acceptance Evidence

Date: 2026-08-05

Scope: SETUP-P0-02 only. This pass covers prerequisite diagnostics,
component-scoped blockers, Safe Mode wording, browser manual-install guidance,
post-installer re-probing, installer contracts, staging, production
compilation, and one guarded UI diagnostic smoke run on this host.

Reproducible build identity, clean-machine matrix validation, Docker/WSL/VM
system acceptance on dedicated machines, and final release testing remain
outside this acceptance pass.

## Outcome

SETUP-P0-02 passes on this host for source contracts, payload staging, final
installer compilation, and guarded UI diagnostic smoke coverage.

The prerequisite page now evaluates Python, Node, browser availability, Docker
Desktop installation, Docker CLI availability, Docker daemon reachability,
Docker image availability, WSL2, virtualization capability, VM detection, and
nested virtualization separately. Only prerequisites required by selected
components can become blockers. Docker, WSL2, virtualization, and VM/nested
virtualization states are surfaced as diagnostics and Safe Mode explanations,
not hard blockers for the installer.

The final UI smoke confirmed that the prerequisite diagnostics are visible
before the Ready page and stopped before installation.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Evaluate Python separately | PASS | `ProbePython` remains independent and writes the detected Python path to generated diagnostics. |
| Evaluate Node separately | PASS | `ProbeNode` remains independent and writes the detected Node path to generated diagnostics. |
| Evaluate browser availability separately | PASS | `ProbeBrowser` now checks Chrome, Edge, and Brave independently, records browser-specific booleans, and keeps an aggregate browser state for Chat Bridge selection logic. |
| Evaluate Docker Desktop separately from Docker CLI | PASS | Setup now records Docker Desktop installation state separately from CLI resolution. Docker Desktop can be present while Docker CLI or daemon checks still fail. |
| Evaluate Docker daemon separately from installed Docker Desktop | PASS | The daemon check requires `docker -H npipe:////./pipe/docker_engine info`; an installed Docker Desktop application is not treated as a running daemon. |
| Evaluate Docker images separately | PASS | Required image checks remain separate from Docker Desktop, CLI, and daemon checks and are written to diagnostics. |
| Evaluate WSL2 separately | PASS | Setup probes `wsl.exe --status` through PowerShell and reports WSL2 as a diagnostic state. |
| Evaluate virtualization separately | PASS | Setup probes `Win32_Processor.VirtualizationFirmwareEnabled` and reports virtualization capability independently. |
| Evaluate VM and nested virtualization separately | PASS | Setup probes `Win32_ComputerSystem` for VM manufacturer/model signals and reports nested virtualization as a derived diagnostic. |
| Block only selected components | PASS | Contract tests verify Docker, WSL2, virtualization, and VM/nested diagnostics do not append blockers. Python, Node, and browser blockers remain scoped to selected components that require them. |
| Missing browser does not block pure STDIO components | PASS | A dedicated contract test verifies that missing Chrome/Edge/Brave only blocks selected Chat Bridge browser integration, not pure STDIO component selections. |
| VM without nested virtualization receives explicit explanation | PASS | Setup includes a VM/no-nested fixture and user-facing diagnostic text explaining that Docker/WSL2 may fail inside a VM unless nested virtualization is enabled on the host. |
| Docker Desktop installed does not imply running daemon | PASS | Contract tests require separate Docker Desktop and daemon states and require daemon validation through `docker info` against the Docker named pipe. |
| Safe Mode remains understandable and installable | PASS | Safe Mode messaging explains that Docker/WSL2/virtualization issues can be resolved later. These diagnostics are not hard blockers. |
| Re-probe after third-party installers | PASS | Contract tests verify that prerequisite refresh paths re-run probes and write actual detected paths and runtime states after external installer actions. |
| Update UI fixture/contracts | PASS | Installer source contracts increased to 54 passing tests, and UI smoke supports `-ExpectSetupP002Diagnostics`. |
| Manual Chrome and Brave extension guide | PASS | `docs/WINDOWS_INSTALLER_GUIDE.md` now documents manual extension installation for Chrome and Brave, the installed extension directory, Native Messaging host checks, repair flow, and common wrong-directory/bridge-unavailable failures. |
| Full staging and production compile | PASS | `build.ps1 -ValidateOnly -SkipNodeBuild` staged payloads successfully, and `build.ps1 -SkipNodeBuild` compiled the final production installer. |

## Verification Commands

Executed in `<REPOSITORY_ROOT>\installer\windows`:

```powershell
$script = Get-Content -LiteralPath 'tests\installer-contract.Tests.ps1' -Raw
[scriptblock]::Create($script) | Out-Null
```

Result: PowerShell syntax validation passed.

Executed in the same directory:

```powershell
$script = Get-Content -LiteralPath 'tests\installer-ui-smoke.ps1' -Raw
[scriptblock]::Create($script) | Out-Null
```

Result: PowerShell syntax validation passed.

Executed in the same directory:

```powershell
.\build.ps1 -ValidateOnly -SkipNodeBuild
```

Result:

```text
ValidateOnly complete. Payload staged and verified; ISCC was not invoked.
```

Executed in the same directory:

```powershell
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Result: all 54 installer contract tests passed.

Executed in the same directory:

```powershell
.\build.ps1 -SkipNodeBuild
```

Result:

```text
PLwC Windows installer build complete:
<REPOSITORY_ROOT>\installer\windows\dist\PLwC-Setup-0.2.0-rc18.dev9-installer-r8.exe
```

Executed in the same directory:

```powershell
.\tests\installer-ui-smoke.ps1 -Language english -FixtureGuardsInstallation -MaximumNextClicks 20 -ExpectSetupP002Diagnostics
```

Result: the smoke reached the Ready page, stopped before installation, and
printed:

```text
SETUP_P0_02_DIAGNOSTICS_VISIBLE
```

Executed in the same directory:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath `
  '.\dist\PLwC-Setup-0.2.0-rc18.dev9-installer-r8.exe'

Get-FileHash -Algorithm SHA256 -LiteralPath `
  '.\dist\PLwC-0.2.0-rc18.dev9-payload-manifest.json'
```

Result:

```text
PLwC-Setup-0.2.0-rc18.dev9-installer-r8.exe
SHA256 6769715AD73E69758B81DABA5DDD5466890968E626EE20A0701B2DBEEE2CC99F

PLwC-0.2.0-rc18.dev9-payload-manifest.json
SHA256 2ACBD1A7C61C236C8B7DD8A6607A8F4381B4788F4E07785505112AEDBB81F34A
```

`dist\SHA256SUMS.txt` contains:

```text
2acbd1a7c61c236c8b7dd8a6607a8f4381b4788f4e07785505112aedbb81f34a  PLwC-0.2.0-rc18.dev9-payload-manifest.json
6769715ad73e69758b81daba5ddd5466890968e626ee20a0701b2dbeee2cc99f  PLwC-Setup-0.2.0-rc18.dev9-installer-r8.exe
```

## Non-Final Diagnostic Note

One earlier ungated `build.ps1 -ValidateOnly` / Pester path without
`-SkipNodeBuild` timed out after 600 seconds after Node builds and MCPB staging
work had already run. That timeout was not used as final evidence. The final
accepted staging, contract, compile, hash, and UI smoke evidence above used the
completed commands listed in this document.

## Implementation Boundary

- `installer/windows/PLwCSetup.iss` owns prerequisite probing, diagnostics,
  Safe Mode explanations, component blockers, browser detection, Docker/WSL2/VM
  diagnostics, and Native Messaging registration for Chrome, Edge, and Brave.
- `installer/windows/tests/installer-contract.Tests.ps1` owns the static and
  staged contract checks for SETUP-P0-02.
- `installer/windows/tests/installer-ui-smoke.ps1` owns the guarded UI
  diagnostic visibility smoke marker.
- `docs/WINDOWS_INSTALLER_GUIDE.md` owns the English manual Chrome and Brave
  extension installation and troubleshooting guide.
- `installer/windows/README.md`, `installer/windows/manifests/components.json`,
  `installer/windows/V_MODEL.md`, and `docs/WINDOWS_INSTALLER_PLAN.md` were
  updated for Chrome/Edge/Brave consistency.

## Non-P0-02 Items

- No version bump to 1.0.0 was performed.
- No clean-machine G5/VM acceptance claim was made.
- No P0-03 reproducible build identity change was made.
- No unrelated dirty work in the repository was reset, reverted, or cleaned.
