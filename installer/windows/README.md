# PLwC Windows Installer

This directory builds the selectable Windows installer for the PLwC Gateway,
Claude Desktop MCPB, Codex STDIO, Odysseus STDIO and PLwC Chat Bridge.

Current accepted pre-release candidate: `PLwC-Setup-1.0.0-installer-r24.exe`,
5,218,213 bytes, SHA-256
`b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0`.
It is an explicit unsigned build with Authenticode status `NotSigned`; Windows
may display an unknown-publisher warning. Its public reviewer copy is bound to
the versioned GitHub pre-release and must not be replaced by an older EXE.

Preserved r25 development predecessor: `PLwC-Setup-1.0.0-installer-r25.exe`,
5,221,208 bytes, SHA-256
`e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c`.
It is also explicitly unsigned and retained as rollback evidence. The r26 source
is under phased validation; no r26 production or distributable EXE exists until
the Product Owner explicitly approves that build after the remaining gates.

The end-user artifact is an Inno Setup executable:

```text
dist/PLwC-Setup-<gateway-version>-<installer-revision>.exe
```

Each production compile also writes a deterministic external identity record,
the payload manifest and `SHA256SUMS.txt`. The identity record binds the exact
setup EXE SHA-256 to the installer revision, Gateway, Node Bridge, Browser
Extension, Native Launcher and the acceptance record for that build. The running
installer calculates the same EXE hash from `{srcexe}` and records it in the
installation summary, diagnostic log and generated `selection.ini`.

No PowerShell file is an end-user installation entry point. `build.ps1` and
the files under `tests/` are maintainer-only build and verification tools.
The bilingual end-user instructions are in
[`docs/WINDOWS_INSTALLER_GUIDE.md`](../../docs/WINDOWS_INSTALLER_GUIDE.md).

The wizard always opens with an explicit German/English language choice and
defaults to Gateway-only. The selected language is used consistently for
standard wizard controls, prerequisite status, progress and error messages.
Before any directory or configuration page, it checks the prerequisites for
the current component selection. Missing Gateway, Claude Desktop or Chat
Bridge requirements block only the affected valid plan; missing Codex or
Odysseus produces a prepared snippet warning. Docker remains optional and
records a visible Safe Mode expectation when its local daemon or required
images are unavailable.

Missing Python and its Microsoft Visual C++ runtime, Node.js (for a selected
Chat Bridge) and Docker Desktop each have an initially unchecked automatic
setup option plus buttons to the official vendor pages. Start Setup normally
so Native Messaging, the Startup-folder Chat Bridge shortcut and `%APPDATA%`
belong to the signed-in user. Node.js and
Docker/WSL request Windows administrator approval through UAC only when their
installation needs it. Claude Desktop and Chrome, Edge or Brave remain manual
prerequisites.
Required Python/Node choices disable Next until the user selects a resolution;
the Next button keeps its short localized caption while a separate status line
explains the required action or retry.

New installations use stable runtime directory names:

```text
%APPDATA%\PLwC\app\gateway
%APPDATA%\PLwC\app\bridge
```

When Setup detects a complete installation, it switches to update mode before
the directory and runtime pages, reuses all persisted paths and settings, and
skips repeated questions. Existing legacy or versioned directories remain in
place; update and repair do not rename them or recreate user data. Persisted
`selection.ini` state takes precedence over stale duplicate registry values.

Setup disables prerequisite choices and Back/Next navigation while installed
components are being detected. After Next is clicked, it snapshots the selected
automatic setup plan and keeps one progress page visible across downloads,
elevated vendor installers and the final detection pass. The selection is not
cleared between child installers; it is updated only after postflight detection
has established the resulting component state. The main setup remains
non-elevated because its application data, Native Messaging registration and
Startup-folder shortcut are per-user. The verified system-wide child installers receive
UAC elevation when required.

The same page separates the build-derived PLwC payload size from additional
Python, Node.js and Docker Desktop downloads. It reports WSL/image storage and
variable first-use model caches as separate classes. Values that cannot be
known before enablement, image pulls or model selection are displayed as
`unknown`, never as null or zero. Vendor estimates are versioned in
`assets/prerequisite-sizes.iss`.

A failed vendor installation reports the component, exit code, diagnostic log
path and next action. Python installer, pip, Visual C++ runtime, Node MSI and
Docker setup logs are
stored below `%APPDATA%\PLwC\logs\setup\prerequisites`. Node MSI uses verbose
Windows Installer logging, and common cancellation, fatal-error and
installation-in-progress codes receive distinct guidance. UAC launch failures
caused by an unresolved executable path are also reported separately from a
vendor installer exit code.
After `pip`, Setup imports every required Python module through the same
absolute interpreter and logs its path or full traceback. A remaining import
failure triggers one repair attempt for the pinned Visual C++ runtime.

The Chat Bridge keeps the stable unpacked development ID
`nlogfcafjdfdoknpkbehjgihpafpipdb` separate from the assigned Chrome Store ID
`feceodobnhefdbfgmbinkndhogpfkicb` and Edge Store ID
`nncomjknhhlgcmkmlaljhkiojcnpmflb`. When Chat Bridge is selected, Setup writes
one Native Messaging manifest allowing exactly those three origins and no
wildcard, registers it automatically under the current user's Chrome, Edge and
Brave registry keys, and creates a per-user Startup-folder shortcut targeting
the native launcher directly. The launcher waits 20 seconds after sign-in and
then verifies the Bridge. The wizard no longer asks the
user to copy an extension ID or run a PowerShell registration script.
`bridge/scripts/healthcheck.mjs` and `bridge/scripts/launch-bridge.mjs` are
required staged payloads because the native launcher uses both in the installed
layout. Registration, migration, startup and uninstall call the native launcher
directly; the normal integration path does not invoke PowerShell or
`ExecutionPolicy Bypass`. An owned legacy PLwC scheduled task is removed during
update, while a foreign same-name task is preserved.

Setup is fail-closed for a selected Chat Bridge. Before it can record
`installation_completed/status=success`, it verifies Native Messaging status,
the Startup shortcut, the exact embedded/runtime build identity and exactly
eight public tools. Any failed phase records `chat_bridge_postflight` with
`status=failure`, rolls back the new Native Messaging registration and aborts
instead of showing a successful completion.

The directory and runtime forms are split into compact pages for `1366x768`.
Qdrant and Persona Layer settings use checkboxes. The PLwC logo is embedded in
the setup executable, uninstaller and wizard header.

Setup installs self-contained English and German Getting Started pages below
`%APPDATA%\PLwC\app\docs`. The page matching the explicit Setup language is
selected on the Finish page and remains available through the localized Start
menu entry. It begins with separate completion paths for Gateway-only, Claude
Desktop MCPB, Codex STDIO, Odysseus STDIO and Chat Bridge installations. The
guide then explains natural-language tool use and the purpose, appropriate use,
and write behavior of Status, Describe, onboarding, compile modes, Reflection,
Governor, diary writes, Trashcan moves, Persona promotion, and the narrow
`force` boundary. The Bridge Primer is explicitly limited to Chat Bridge; native
MCP clients receive tool schemas directly. The technical installation summary
remains a separate, default-off Finish action.

## Build

Requirements:

- Windows 10 or newer;
- Python 3.11 or newer;
- Node.js 22.12 or newer when the Chat Bridge payload is built;
- Inno Setup 6 with `ISCC.exe`;
- for a signed build: Microsoft-signed x64 `signtool.exe` from the Windows SDK,
  a currently valid code-signing certificate with an accessible private key in
  `Cert:\CurrentUser\My`, and an RFC 3161 timestamp service.

From the repository root:

```powershell
.\installer\windows\build.ps1 -ValidateOnly
.\installer\windows\build.ps1 -Unsigned
.\installer\windows\build.ps1
```

The first command validates contracts and stages the payload without compiling
an installer. It is an unsigned diagnostic operation and must never be treated
as a distributable build. The second command explicitly compiles an unsigned
installer and marks the launcher, setup EXE and external build identity as
`NotSigned` / `explicit_unsigned`. Windows may identify its publisher as
unknown. Its isolated output is written below
`installer/windows/.unsigned-build-r26/`, preserving the normal `stage/` and
`dist/` evidence trees. The third command repeats validation, compiles the setup EXE, signs
both the Native Messaging launcher and the setup EXE with SHA-256, applies
SHA-256 RFC 3161 timestamps, and verifies both signatures before writing the
external build identity. Without `-Unsigned`, it fails closed when signing is
not fully configured.

Configure the production signing inputs either as parameters or user/process
environment variables:

```powershell
$env:PLWC_SIGNTOOL_PATH = 'C:\path\to\x64\signtool.exe'
$env:PLWC_SIGNING_CERT_THUMBPRINT = '<40-character SHA-1 certificate thumbprint>'
$env:PLWC_SIGNING_TIMESTAMP_URL = 'https://<provider-rfc3161-endpoint>'
\.\installer\windows\build.ps1
```

`PLWC_SIGNTOOL_PATH` is accepted only when the tool carries a valid Microsoft
Authenticode signature. The certificate must be in the current user's personal
certificate store, include the Code Signing EKU, be currently valid, and expose
its private key to SignTool. Timestamping is mandatory so an accepted release
signature remains verifiable after certificate expiry. Generated `stage/` and
`dist/` directories are not source artifacts.

The embedded Pester validation uses the isolated
`installer/windows/.test-build/` root. It must not reset or overwrite the real
`installer/windows/stage/` and `installer/windows/dist/` evidence directories.

The embedded Python runtime lock is generated from
`assets/runtime-requirements.in` for Windows x64 and Python 3.13:

```powershell
uv pip compile installer/windows/assets/runtime-requirements.in `
  --python-version 3.13 `
  --python-platform x86_64-pc-windows-msvc `
  --generate-hashes `
  --no-emit-index-url `
  --no-header `
  --output-file installer/windows/assets/mcp-runtime-lock.txt
```

## Gates

`V_MODEL.md` defines G0 through G6 and the required evidence. A successful
compile proves only G3. The setup must not be called a release candidate until
component verification (G4), clean Windows system validation (G5) and release
acceptance (G6) have passed for the exact EXE SHA256.

The first development build deliberately prepares Codex and Odysseus STDIO
configuration snippets when a supported host schema cannot be positively
identified. It does not overwrite unknown client configuration files.
