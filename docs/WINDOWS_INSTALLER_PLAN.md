# PLwC Windows Installer Plan

Status: requirements corrected after failed Clean-Windows-11 prerequisite test
Scope: Windows-first installer for PLwC Gateway plus optional client targets.

This plan captures the intended installer shape for PLwC after the rc18 MCPB
and rc19 Chat Bridge work. The installer must be selectable: a user can install
only one client route, several routes, or all supported routes from the same
shared PLwC configuration.

## Goals

- Deliver one Windows setup executable as the only end-user installer entry
  point. A `.ps1` file is never the installed product or the documented normal
  installation route.
- Offer explicit component selection instead of one fixed install path.
- Keep every page fully usable at `1366x768`; split long forms across pages
  and use checkboxes for Boolean values.
- Provide complete German and English installer UI, including all custom
  labels, validation/prerequisite messages, previews and completion text.
- Always show an explicit German/English language chooser before the welcome
  page. Preselect the matching Windows UI language and fall back to English.
- Explain before any prerequisite download that Python, Node.js, Docker
  Desktop and Windows features can require administrator approval. Provide a
  controlled elevated restart while retaining the selected language and plan.
- Show the PLwC payload size separately from prerequisite download sizes,
  estimated installed sizes and variable first-run Docker/WSL/image storage.
- Keep exactly one PLwC public gateway boundary: `plwc-gateway`.
- Reuse one shared workspace/profile/config choice across selected targets.
- Generate safe defaults for all directories and first configuration fields.
- Support both normal-user and maintainer/developer paths.
- Never install raw PBA, PLfC, Desktop Commander, host-shell, filesystem or
  second PLwC MCP servers.
- Keep hosted ChatGPT web/custom-app remote MCP separate from the local Chat
  Bridge route.

## Component Choices

The installer UI should expose these checkboxes:

| Component | Default | Result |
| --- | --- | --- |
| PLwC Gateway runtime | Required | Installs or selects the `plwc-gateway` runtime used by every target. |
| Claude Desktop MCPB | Optional | Installs or prepares the verified `.mcpb` route for Claude Desktop. |
| STDIO for Codex | Optional | Creates a `plwc-gateway` stdio config snippet or writes a verified Codex config target when supported. |
| STDIO for Odysseus | Optional | Creates or writes one external stdio MCP server config for Odysseus. |
| PLwC Chat Bridge | Optional | Builds/installs the local browser extension, loopback bridge and optional native launcher. |
| Docker readiness and setup | Optional | Checks Docker Desktop and required images. With explicit consent, setup downloads and installs Docker Desktop; otherwise it offers the official download page. |
| Smoke tests | Recommended | Runs selected target checks after installation. |

`Select all` is valid. Each selected target must receive the same effective
workspace/profile defaults unless the user explicitly overrides a target.

## Clean Windows 11 Finding

The development candidate `PLwC-Setup-0.2.0-rc18.dev9.exe` is superseded and
must not be promoted. A manual test on a clean Windows 11 system showed that
the setup completed with Gateway, Claude MCPB, Codex, Odysseus and Chat Bridge
selected even though Python, Node.js and the selected client applications were
not installed. Chrome was not installed and the setup showed no browser
detection result. Docker was also missing, but the setup did not visibly state
that PLwC would start with Safe Mode expected.

This is a product failure, not a blocked test. A copied payload or generated
snippet is not an installed, runnable integration. The next candidate must
implement and verify the component-dependent prerequisite policy below before
G1 through G4 can return to `GO`.

The same Clean-Windows-11 test at `1366x768` also exposed a clipped runtime
configuration page, Boolean values presented as editable `false/true` text and
mixed German/English installer-owned text. These UI and localization defects
also invalidate the current candidate.

## Component-Dependent Prerequisites

Prerequisites must be detected before the write preview and reevaluated when a
component selection changes. The preview and final summary must show every
selected component as `ready`, `blocked`, `prepared` or `safe-mode`, including
the detected executable/application and version where applicable.

| Selected component | Required detection | Missing or invalid result |
| --- | --- | --- |
| PLwC Gateway runtime | A usable Python executable with version `>=3.11` and successful `import mcp` in that exact interpreter | Show `action required`. Offer an explicit, initially disabled option to download and install the pinned official Python package plus the complete, exactly versioned and SHA-256-hash-locked `mcp` runtime closure, and a separate button for the official Python download page. Install Python packages for the current user. Without a successful recheck, no PLwC payload or configuration may be written. |
| Claude Desktop MCPB | An installed, supported Claude Desktop application | Block Claude MCPB. The user must install Claude Desktop or deselect the component before setup can continue. Do not copy the MCPB and do not claim Claude integration. |
| PLwC Chat Bridge | Node.js meeting the manifest version requirement and at least one supported Chrome, Edge or Brave installation | For missing Node.js, offer an explicit, initially disabled automatic installation of a pinned official Node.js LTS MSI plus a separate official download-page button. The system-wide MSI requires a Windows administrator confirmation. A missing browser remains manual and stops the selected Bridge before any acquisition. Until both checks pass, do not install or register Bridge/native-messaging artifacts. |
| STDIO for Codex | Installed Codex application/CLI and a recognized configuration target | If absent or unknown, warn and continue only in `prepared` mode. Generate the snippet without changing host configuration; the summary must say `prepared - Codex not detected`. |
| STDIO for Odysseus | Installed Odysseus application and a recognized configuration target | If absent or unknown, warn and continue only in `prepared` mode. Generate the snippet without changing host configuration; the summary must say `prepared - Odysseus not detected`. |
| Docker readiness | Docker CLI, reachable daemon and required local images | Do not block core installation. Offer an explicit, initially disabled option to download and install the pinned official Docker Desktop package, and a separate button for the official Docker installation page. Never accept Docker license terms or pull images automatically. Until the daemon and images are ready, show a warning, record `safe_mode_expected=true`, and state that sandbox/document-worker operations remain unavailable. |

Detection must use known executable locations, uninstall/app registration and
version probes as appropriate; a text placeholder or a user-selected checkbox
does not count as successful detection. The UI uses `action required` instead
of `blocked`. A component needing action must name the missing prerequisite and
offer retry, explicit automatic setup where supported, an official manual
download page, deselection of an optional component, or setup cancellation.

Automatic prerequisite acquisition is permitted only after an explicit user
opt-in. It uses HTTPS URLs on official vendor domains, pinned versions and
SHA-256 values. The installer re-runs every prerequisite probe after each
attempt. Silent PLwC setup never implies consent and therefore never downloads
or installs prerequisites. Python and Docker remain user-scoped where their
vendor installers support it; the official Node.js MSI is system-wide and
requires a Windows administrator confirmation. Claude Desktop and browsers
remain manual.

## Installer UI And Languages

`1366x768` is the minimum acceptance resolution. Every standard and custom
page must keep its title, explanatory text, controls and Back/Next/Cancel
buttons fully visible and operable without overlap or clipping. Long directory
and runtime forms must be split into additional pages instead of extending
below the navigation area. Dynamic prerequisite results and translated strings
must not resize controls beyond the usable page area.

Boolean configuration values, including Qdrant and Persona Layer Disabled,
must be represented by labeled checkboxes. Users must not type `true` or
`false` into text fields. Numeric thresholds remain validated numeric inputs;
directory and file values retain appropriate browse controls.

The setup must offer German and English. The standard language dialog must be
shown on every interactive first launch before the welcome page, even when the
Windows UI language is already supported. It preselects the Windows UI language
where possible, permits a manual choice and falls back to English. `/LANG=english`
and `/LANG=german` remain available for managed launches. The selected language
applies without
mixing to all installer-owned visible content:

- standard and custom page titles, descriptions, labels and buttons;
- component names, prerequisite states, warnings and validation errors;
- directory, profile, runtime, preview and progress text;
- cancellation, rollback and fatal-error messages;
- final status, prepared/safe-mode notices and completion/next-action text.

Language selection follows the installer's normal startup flow, defaults to a
supported Windows UI language when possible and remains manually selectable.
Missing translations are a build/test failure; falling back to a different
language inside an otherwise German or English flow is not allowed.

## Administrator And User Context

PLwC data remains user-owned below the selected profile and data roots. The
installer must not silently redirect `%APPDATA%\PLwC` to a different
administrator account when a standard user supplies alternate credentials.

Before any prerequisite download or install, the wizard must:

- state in German or English that Node.js, Docker Desktop and Windows features
  can require administrator approval;
- keep the main setup in the signed-in user's context;
- request UAC only for the individual Node.js, Docker/WSL or Windows operation
  that requires elevation;
- preserve the selected language, component plan and original user-owned data
  roots across that elevated child operation;
- log UAC cancellation and vendor-installer exit codes as named outcomes;
- keep the official vendor-page route available without claiming installation.

The end-user guide explicitly tells users to start Setup normally. This avoids
writing Native Messaging, scheduled-task and `%APPDATA%` state into a different
administrator profile when a standard user supplies alternate credentials.

## Download And Storage Estimates

The component and prerequisite pages must show honest, separate estimates. A
small PLwC setup executable must not imply that Docker, WSL, Python packages or
container images fit into the same size.

Initial planning values for the pinned Windows x64 packages are:

| Item | Approximate download | Storage note |
| --- | ---: | --- |
| PLwC Gateway and Chat Bridge payload | about 20 MB | User-owned PLwC files; exact staged size comes from the build manifest. |
| Python and hash-locked PLwC runtime | about 95 MB | Includes the Python installer and 58 Windows runtime wheels, including the optional Qdrant modules; installed size is approximately 400-1000 MB. |
| Qdrant embedding model | about 100-500 MB on first use | Downloaded only when Qdrant is first used; the exact cache size can vary. |
| Node.js MSI | about 31 MB | The installed system-wide runtime is larger than the MSI. |
| Docker Desktop | about 610 MB | Installed application, WSL distribution and service data require multiple GB. |
| Docker images and model/cache data | variable | First use can require several additional GB; no image is pulled implicitly. |

These numbers are estimates, not a fixed product claim. The build generates a
versioned size manifest with source timestamp, `downloadBytes`,
`installedBytesMinimum` and `firstRunAdditionalBytes` or an explicit `variable`
marker. The wizard shows:

- the exact staged PLwC payload size;
- each selected external download;
- the summed known download size;
- the minimum known local storage requirement;
- a separate warning for variable Docker/WSL/image/model data;
- a free-space check before acquisition and before the final write step.

If current package metadata cannot be established, the wizard says that the
size is unknown instead of displaying zero.

## Default Directories

The installer should present editable directory fields with these defaults:

| Field | Default |
| --- | --- |
| PLwC app root | `%APPDATA%\PLwC\app` |
| Gateway runtime root | `%APPDATA%\PLwC\app\gateway` |
| Chat Bridge root | `%APPDATA%\PLwC\app\bridge` |
| Workspace root | `%APPDATA%\PLwC\workspace` |
| Profiles root | `%APPDATA%\PLwC\profiles` |
| Global config root | `%APPDATA%\PLwC\config` |
| Global runtime state root | `%APPDATA%\PLwC\state` |
| Global audit log root | `%APPDATA%\PLwC\logs` |
| Profile backup root | `%APPDATA%\PLwC\profile_backups` |

Rules:

- workspace and profiles roots must be separate;
- profiles root must not be inside the workspace root;
- app/config/state/log/backup roots must not be exposed as workspace roots;
- source checkouts and mapped development drives must not become default user
  workspace roots;
- selected directories must be created only after the final confirmation step.
- a complete existing installation is an update: stored directories and
  runtime settings are reused and the corresponding wizard pages are skipped;
- existing versioned runtime paths are preserved during an update and are not
  migrated destructively;
- changing the workspace later must update the shared Gateway, Bridge, Codex,
  Odysseus, installer-selection and per-user installer state consistently.

Profile-owned state lives under the selected profiles root, for example:

```text
%APPDATA%\PLwC\profiles\<profile>\governance\config.yaml
%APPDATA%\PLwC\profiles\<profile>\journal.md
%APPDATA%\PLwC\profiles\<profile>\memory.md
%APPDATA%\PLwC\profiles\<profile>\reflection.md
```

The separate global config/state/log roots are for runtime-wide files such as
the active-profile state, optional `security.yaml`, pending plan snapshots and
audit metadata. They are not part of one individual profile. `profile_backups`
is reserved for explicit backup/import/admin flows, not normal profile runtime
state.

## First Configuration

The installer should collect these fields once and map them into each selected
target:

| Field | Default | Env / MCPB key |
| --- | --- | --- |
| Active profile | `default` | `PLWC_ACTIVE_PROFILE_NAME` / `active_profile_name` |
| Workspace path | workspace root above | `PLWC_WORKSPACE_ROOT` / `workspace_path` |
| Profiles path | profiles root above | `PLWC_PROFILE_ROOT` / `profiles_path` |
| Security config | empty | `PLWC_CONFIG_FILE` / `security_config` |
| Memory write threshold | `2` | `PLWC_MEMORY_WRITE_THRESHOLD` / `memory_write_threshold` |
| Persona write threshold | `3` | `PLWC_PERSONA_WRITE_THRESHOLD` / `persona_write_threshold` |
| Temperament write threshold | `2` | `PLWC_TEMPERAMENT_WRITE_THRESHOLD` / `temperament_write_threshold` |
| Qdrant enabled | `false` | `PLWC_QDRANT_ENABLED` / `qdrant_enabled` |
| Persona layer disabled | target preset | `PLWC_PERSONA_LAYER_DISABLED` / `persona_layer_disabled` |

Target preset for `persona_layer_disabled`:

- Claude Desktop MCPB: `false` by default, matching current MCPB metadata.
- PLwC Chat Bridge: import Claude MCPB settings when available; otherwise use
  the shared installer value.
- STDIO Codex/Odysseus: default to the conservative local-client preset unless
  the user chooses full persona context.

The first installer version does not need to complete governed profile
onboarding. It should create the profile root, select the profile name and make
`plwc_status(scope="first_run")` show the next governed onboarding action.

## Target Behavior

### Claude Desktop MCPB

The installer may:

- verify the MCPB SHA256;
- open the MCPB file and guide the user through Claude Desktop Developer Mode;
- optionally prepare a direct MCP connector fallback if the Claude Desktop MCPB
  installer is broken;
- write clear instructions that Claude Desktop must be fully closed before
  manual config edits.

The installer must not silently enable unrelated MCP servers.

### STDIO for Codex

The installer should produce a single `plwc-gateway` stdio definition using:

```text
command: <absolute python executable>
args: [<gateway runtime root>\server.py]
env: shared PLwC configuration
```

Automatic config-file mutation is allowed only after the exact Codex config
location and schema are known and verified for the installed host. Until then,
the safe MVP is to generate a ready-to-paste snippet and record the target as
`prepared`.

### STDIO for Odysseus

The installer should create or present the same one-server stdio definition for
Odysseus. When the Odysseus config path is known, it may write the config after
backing up the previous file and validating that no second PLwC server is
introduced.

### PLwC Chat Bridge

The installer should:

- install the prebuilt Bridge, extension and native-launcher artifacts;
- register Chrome, Edge and Brave Native Messaging for the stable unpacked extension
  ID without asking the user to copy it;
- keep loopback fixed to `127.0.0.1:3007`;
- create a limited per-user scheduled task that starts and verifies the Bridge
  after Windows sign-in;
- open the extension folder for loading as an unpacked extension;
- verify that Status -> Reconnect can start the WebSocket bridge after the
  native launcher is registered;
- restore previous task/settings after a failed repair or upgrade and remove
  all owned integration state during uninstall.

Later release packaging may replace the unpacked extension flow with a signed
browser-store extension while retaining a controlled stable identity.

## Installer Flow

1. Show the German/English language chooser and then the localized beta/safety
   notice.
2. Select components on a page that fits at `1366x768`; show the PLwC payload,
   optional download and storage estimates without crowding the controls.
3. Detect the prerequisites for the current selection and show a localized status for
   each component. Mark Gateway without Python `>=3.11` plus the required
   `mcp`, `fastembed` and `qdrant-client` modules, Claude
   without Claude Desktop, and Chat Bridge without Node.js or Chrome/Edge/Brave as
   `action required`. Missing Codex/Odysseus enters warned `prepared` mode.
   Missing Docker enters visible `safe-mode` status. Missing Claude or a
   supported browser stops on this report page before any prerequisite is
   downloaded or installed; the user must resolve it or go back and deselect
   the affected optional component. Missing Node.js proceeds to the explicit
   acquisition page when Chat Bridge is selected.
4. Before acquisition, explain administrator requirements, verify the complete
   plan and offer a controlled elevated child launch when required. Keep the
   per-user Setup process non-elevated. When Python,
   Node.js or Docker needs attention, offer unchecked automatic
   setup choices plus buttons to their official download pages and a status
   recheck. Keep `Next` disabled until every missing required acquisition has
   an explicit selection. Lock choices and Back/Next navigation while detection
   runs. Download and install only after selection and a second side-effect-free
   preflight, verify pinned SHA-256 values and recheck. Snapshot the selected
   acquisition plan and keep one progress page active across every download,
   vendor installer, and the final postflight check; do not expose a cleared
   acquisition page between child operations.
   A failed action returns a named retry state without an additional generic
   gate message; a failed required Python or Node.js step prevents a following
   Docker step. Long downloads/installations use localized progress pages.
   Restart exit codes stop all remaining prerequisite actions. The Python
   module set is installed from the embedded full hash lock; Docker uses its
   per-user installation mode; Node.js uses the official system-wide MSI with
   Windows administrator confirmation.
5. Choose directories or accept defaults across as many pages as required to
   remain unclipped.
6. Choose first PLwC configuration values or accept defaults; Boolean values
   use checkboxes.
7. Preview exactly what will be written, including prerequisite decisions,
   download/storage estimates, prepared targets and `safe_mode_expected`.
8. Install selected components.
9. Register selected client targets.
10. Run selected smoke tests.
11. Show final status and next actions per target without calling an unresolved or
    merely prepared target installed.

## Smoke Matrix

| Target | Minimum smoke |
| --- | --- |
| Gateway runtime | `plwc_status(scope="runtime")` returns server `plwc-gateway` and eight tools. |
| Claude Desktop MCPB | Claude shows one `plwc-gateway` server and exactly eight public tools. |
| STDIO Codex | Generated config contains one server and the expected env mapping. Live smoke only when Codex config automation is verified. |
| STDIO Odysseus | Odysseus starts one stdio server and lists exactly eight tools. |
| Chat Bridge | Loopback bridge lists eight tools and `plwc_status(scope="runtime")` succeeds. |
| Installer UI | Every page in German and English fits at `1366x768`; all Boolean controls are checkboxes and longest messages remain visible. |

## Browser Store Distribution Track For 1.0.0

Store delivery is a separate serial track after SETUP-P1-01 and the corrective
SETUP-P0-02-FIX-01 prerequisite-orchestration acceptance. The accepted
BRIDGE-P0-02-FIX-01 onboarding continuation and aligned Bridge build identity
and its SETUP-P0-02-FIX-02 `installer-r12` payload integration are also
prerequisites. Creating draft Store identities is an external gate, not
authorization to publish. The PLwC core remains unchanged; Chat Bridge Store
work precedes Windows Setup Store integration and requires a renewed H2 handoff.

1. `STORE-G0-01` establishes verified Chrome Web Store and Microsoft Edge
   publisher ownership, public support/privacy URLs, and unpublished items that
   provide the final Store extension IDs. No credentials, payment information,
   recovery material, or publisher tokens enter the repository.
2. `BRIDGE-P0-03` builds privacy-filtered Chrome/Brave and Edge ZIP packages
   with `manifest.json` at the archive root. Its canonical identity contract
   distinguishes Chrome Store, Edge Store, and development IDs. Native
   Messaging permits the exact approved origins without wildcards. Bridge,
   browser, Extension, and launcher acceptance is repeated before H2 is reissued.
3. `SETUP-P0-05` registers every approved Store origin for the signed-in Windows
   user, opens the appropriate Store listing after install or Repair, and keeps
   the browser's explicit Add/Get consent step. Unpacked loading is not the
   default end-user path.
4. `STORE-P0-02` submits the exact versioned packages with complete purpose,
   permission, data-use, privacy, support, reviewer, screenshot, and listing
   material. Publication stays deferred or otherwise controlled until Chrome,
   Brave, and Edge end-to-end tests pass.
5. `SETUP-P0-04` and common G4/G5 testing use the exact Store item IDs, Store
   package versions, Native Launcher, Setup EXE SHA-256, and build evidence that
   are candidates for public `1.0.0` release.

The browser Store installs only the extension. PLwC Setup remains the supported
delivery path for the Gateway, loopback Bridge, and Native Launcher. Setup may
open the Store listing but must never bypass browser consent or claim that the
Store installed the native application.

## Implementation Phases

Implementation follows the gated V-model in
`installer/windows/V_MODEL.md`. Gate evidence is kept with the installer so
requirements, implementation and verification remain in the same repository.

### Phase 1: Executable Installer Skeleton

- Implement `installer/windows/PLwCSetup.iss` as the authoritative Inno Setup
  definition.
- Expose component selection, editable directories and first profile defaults
  directly in the setup UI.
- Split custom pages to fit `1366x768`, use Boolean checkboxes and keep all
  navigation controls visible.
- Store every installer-owned visible string in complete German and English
  language resources, including errors and completion text.
- Produce `PLwC-Setup-<version>.exe`; do not ship a PowerShell installer.
- Keep any PowerShell file under `installer/windows` maintainer-only for
  staging, contract tests or CI.

### Phase 2: Deterministic Payload And Verification

- Stage the privacy-filtered gateway runtime, verified MCPB, built Chat Bridge,
  browser extension, native launcher and public-safe documentation.
- Generate SHA256 evidence for every staged artifact.
- Run component and safety contract tests before invoking the installer
  compiler.
- Compile the EXE only from a stage tree that passed the preceding gate.

### Phase 3: Client Integration And Release Candidate

- Detect component prerequisites before any write and apply the normative
  block/warn/prepared/safe-mode matrix above.
- Register only client targets whose installed schema is positively detected
  and supported.
- Generate non-destructive prepared snippets for unknown Codex or Odysseus
  schemas.
- Exercise install, repair/re-run and uninstall in a disposable Windows user
  environment.
- Record system and acceptance evidence before a setup EXE is called a release
  candidate.

## Repository Layout

```text
installer/windows/
  PLwCSetup.iss                 Inno Setup source for the end-user EXE
  V_MODEL.md                    gates and requirement traceability
  build.ps1                     maintainer-only stage/build entry point
  manifests/                    component and payload contracts
  tests/                        non-destructive installer contract tests
  stage/                        generated, ignored build input
  dist/                         generated setup EXE and checksums
```

PLwC Gateway remains at the repository root and PLwC Chat Bridge remains under
`integrations/plwc-chat-bridge`. The installer owns packaging and integration,
not duplicate product source trees.

## Non-Goals

- No prerequisite download or installation without explicit interactive consent.
- No automatic acceptance of Docker Desktop license terms or implicit image pulls.
- No public tunnel to the raw PLwC gateway.
- No hidden telemetry.
- No raw host shell or filesystem MCP server installation.
- No automatic mutation of unknown host config formats.
- No final-release claim while artifacts remain unsigned.
