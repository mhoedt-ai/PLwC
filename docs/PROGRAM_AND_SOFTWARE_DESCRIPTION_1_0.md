# PLwC 1.0 - Program and Software Description

- Document status: current public technical description
- Product version: `1.0.0`
- Windows Setup revision: `installer-r24`
- Last verified: 2026-08-30

## 1. Release position

PLwC 1.0 is a local, model-independent governance gateway for AI tool access,
persistent context and controlled memory. The implementation and the Windows
Setup candidate identify as 1.0.0. The current Windows artifact is an explicit
unsigned pre-release candidate, not a production-certified release.

| Item | Current identity or result |
| --- | --- |
| Windows Setup | `PLwC-Setup-1.0.0-installer-r24.exe` |
| Public reviewer URL | `https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r24/PLwC-Setup-1.0.0-installer-r24.exe` |
| Setup SHA-256 | `b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0` |
| Setup size | 5,218,213 bytes |
| Setup signature | Authenticode `NotSigned`; explicit unsigned build |
| Gateway MCPB | `plwc-gateway-1.0.0.mcpb` |
| Repository MCPB SHA-256 | `5e870f40b9b3faea79d3997af9c657ef62c11295e85635a049214f7b63678fe7` |
| Gateway | `1.0.0` |
| Node Bridge | `1.0.0` |
| Browser Extension | `1.0.0` |
| Native Launcher | `1.0.0` |

Chrome and Edge contain submitted 1.0.0 Store candidates. On 2026-08-30, Chrome
entered pending review as a private trusted-tester item with automatic
publication disabled. Edge entered review as hidden and link-only. Neither item
is an installable Store release until its review path succeeds, so live
Store-signed identity acceptance remains pending.

## 2. Product purpose

PLwC is the independent policy and governance layer between an AI host and
local capabilities. It is not a language model, an autonomous agent or a
general unrestricted desktop-control service.

```text
AI host and model
       |
       v
PLwC public MCP facade
       |
       v
validation -> intent -> policy -> governed adapter
       |
       v
workspace, documents, profiles, memory, audit and sandbox
```

The public boundary is exactly one MCP server named `plwc-gateway`. Raw profile
cores, Commander-style filesystem servers and unrestricted host shells are not
part of the PLwC public surface.

## 3. Components

| Component | Responsibility |
| --- | --- |
| PLwC Gateway | Python MCP stdio server, validation, intent construction, policy enforcement, audit metadata and the eight-tool public facade. |
| Claude Desktop MCPB | Packaged local Gateway route for Claude Desktop. |
| PLwC Chat Bridge | Loopback-only Node.js WebSocket-to-MCP bridge for the signed-in ChatGPT web UI. |
| Browser Extension | Manifest V3 panel, primer, call/result rendering, confirmation controls and local connection management for Chromium browsers. |
| Native Launcher | Per-user Native Messaging host that starts or verifies the local Bridge after browser or PC restarts. |
| PLwC Configuration | Authenticated loopback configuration UI for shared runtime settings, workspace changes and diagnostics. |
| Windows Setup | Bilingual per-user installer, updater and repair path for the selected components and prerequisites. |

The Gateway, Node Bridge, extension and Native Launcher report their identities
at runtime. The Chat Bridge rejects a mismatched peer before enabling tool
execution.

## 4. Supported client routes

| Client | Route | Current state |
| --- | --- | --- |
| Claude Desktop | Local MCPB / stdio | Supported and smoke-tested. |
| Codex | Prepared local stdio configuration | Setup generates a snippet; automatic mutation of unknown client configuration is intentionally disabled. |
| Odysseus | Prepared local stdio configuration | Local route supported; setup generates a snippet when direct configuration cannot be verified safely. |
| ChatGPT web | Browser Extension -> loopback Bridge -> local Gateway | Implementation and local Store-origin readiness pass; Store-signed installation remains pending review. |
| Hosted ChatGPT custom app | Authenticated remote MCP facade | Not part of 1.0; the local MCPB must not be exposed through an unauthenticated public tunnel. |

## 5. Public MCP facade

PLwC 1.0 exposes exactly eight tools:

| Tool | Responsibility |
| --- | --- |
| `plwc_status` | Reports runtime, profile, sandbox and first-run state. |
| `plwc_describe` | Describes tools, operations, schemas, plan types and common denial reasons. |
| `plwc_profile` | Loads, inspects, activates and compiles governed profiles and provides read-only diagnostics. |
| `plwc_reflection` | Writes semantically validated reflection entries through the governed reflection path. |
| `plwc_governor` | Plans and, only after confirmation, applies governed profile, memory, persona and condensation changes. |
| `plwc_sandbox_run` | Runs approved Python or shell work inside the Docker sandbox without host-shell fallback. |
| `plwc_workspace_operation` | Performs bounded list, search, read, write, copy, move, rename, exact-replace and binary operations inside configured roots. Public delete is absent. |
| `plwc_document_operation` | Creates and inspects Office/PDF artifacts, performs bounded PDF/ZIP operations and reads supported workspace images. |

Earlier individual tool names are internal or historical. They must not appear
as additional public MCP tools.

## 6. Request and confirmation model

A normal request follows this sequence:

1. validate the public operation and parameters;
2. resolve paths and profile targets against configured roots;
3. construct an explicit intent;
4. obtain a policy decision;
5. dispatch only an allowed request;
6. normalize the result and record relevant local audit metadata.

Read-only Chat Bridge calls may run automatically after a visible delay.
Recognized writes, Governor `apply`, sandbox execution and unknown operations
remain subject to the configured confirmation rules. Automatic confirmation
for recognized writes and sandbox calls is split into two separate,
default-off settings with visible warnings. An ambiguous mutating timeout is
not automatically retried.

## 7. Workspace and profile boundaries

Workspace tools are confined to configured roots. Parent traversal, protected
profile/governance targets and path escapes are denied. Persistent profile and
memory changes use the dedicated profile, reflection and Governor flows.

A new Windows installation creates only these standard workspace directories:

```text
Tagebuch/
Temp/
Trashcan/
```

`Trashcan` is an ordinary governed move target, not an automatic deletion
service. Setup does not create `Inbox`, clean the workspace or delete existing
content.

The workspace can be changed later in **PLwC Configuration**. Saving a new
absolute path updates the shared configuration and creates missing standard
directories. Existing files are not moved, overwritten or deleted. Running
clients need restarting only when they still display the previous path.

## 8. Windows installation and update behavior

Start Setup normally as the signed-in Windows user. The main installer remains
non-elevated so `%APPDATA%`, Native Messaging and scheduled-task state belong to
that user. Only selected prerequisite installers request elevation when needed.

Fresh installations use stable, version-independent runtime paths:

```text
%APPDATA%\PLwC\app\gateway
%APPDATA%\PLwC\app\bridge
```

The package filename may contain the product version; the runtime directory
does not. An existing complete installation is detected before the directory,
profile and runtime pages. Setup then switches to update mode, skips repeated
questions and reuses the stored app, Gateway, Bridge, workspace, profile,
configuration, state, log and backup paths. Existing legacy or versioned
runtime paths are preserved rather than renamed or duplicated.

Persisted `selection.ini` state is authoritative over stale duplicate registry
values. Configuration changes mirror the current shared paths, profile,
thresholds and runtime choices back into the installer state so a later update
does not restore an older workspace.

The canonical desktop shortcut is `PLwC-Konfiguration`. Update and repair
remove the owned legacy name variants before creating one shortcut with the
PLwC icon. It launches the configuration UI through `pythonw.exe` when
available, with a safe `python.exe` fallback.

## 9. Important local files

Default locations are shown below. A user-selected configuration root changes
the corresponding configuration paths.

| Purpose | Default path |
| --- | --- |
| Shared Gateway settings | `%APPDATA%\PLwC\config\gateway-settings.json` |
| Governed active profile | `%APPDATA%\PLwC\config\active_profile.json` |
| Installer selection and identity | `%APPDATA%\PLwC\config\installer\selection.ini` |
| Installation summary | `%APPDATA%\PLwC\config\installer\installation-summary.txt` |
| Native Messaging manifest | `%APPDATA%\PLwC\config\native-messaging\plwc.chat_bridge.launcher.json` |
| Setup diagnostics | `%LOCALAPPDATA%\PLwC\logs\setup\installer-diagnostic.log` |
| Installed local guides | `%APPDATA%\PLwC\app\docs` |

Gateway calls resolve governed active-profile state first, then shared
settings, host/extension configuration and finally product defaults. Saving
ordinary settings does not silently activate another profile.

## 10. Chat Bridge identity and transport

The extension-origin network boundary is the fixed loopback endpoint:

```text
ws://127.0.0.1:3007/message
```

The Native Messaging manifest allows only the three approved origins:

| Track | Extension ID |
| --- | --- |
| Development / unpacked | `nlogfcafjdfdoknpkbehjgihpafpipdb` |
| Chrome Store | `feceodobnhefdbfgmbinkndhogpfkicb` |
| Edge Store | `nncomjknhhlgcmkmlaljhkiojcnpmflb` |

No wildcard origin is allowed. The development identity is not Store identity
evidence. A real Store acceptance must install the Store-signed package and
verify Native Messaging, `8 / 8` tools, confirmations, restart recovery and the
missing-native-host state under that exact Store ID.

## 11. Browser workflow

On a supported ChatGPT page, the PLwC icon opens the panel. A ready state shows
the local endpoint, a valid common build identity and exactly `8 / 8` tools.
The Primer tab generates and inserts the versioned Bridge Primer into the
ChatGPT composer; the user sends it through the existing ChatGPT session.

The extension renders visible tool-call cards, keeps confirmations explicit,
and inserts complete tool results back into the conversation. Large results use
an ordered, SHA-256-bound chunk protocol without semantic truncation. Startup,
service-worker recovery and conversation switches establish a quiet hydration
baseline so old chat content is not executed as new work.

## 12. Security and privacy properties

- one visible PLwC MCP server and eight public facade tools;
- no unrestricted host shell or second filesystem MCP in the PLwC boundary;
- protected profile and governance files cannot be written through workspace
  operations;
- sandbox execution uses Docker with no silent host-shell fallback;
- loopback-only Bridge transport and exact extension origins;
- local audit metadata for relevant decisions without intentionally logging raw
  private content;
- no publisher server contacted by the browser extension;
- no PLwC username, password, API key or paid service required by the extension;
- no external URL fetching for document assets at runtime;
- fail-closed behavior for missing engines, missing sandbox prerequisites,
  identity mismatch and policy denial.

PLwC cannot protect data that the user or host sends directly to a cloud model
outside the PLwC tool boundary.

## 13. Document and sandbox capabilities

The governed Document Worker supports creation of DOCX, XLSX, PPTX and PDF;
bounded PDF inspection, extraction, merge, split and rotation; bounded ZIP
creation, inspection and extraction; and governed reads of PNG, JPEG, WEBP and
first-frame GIF images. Form filling, OCR, redaction, PDF/A claims, macros,
LibreOffice/Pandoc conversion and HTML/CSS rendering are not part of 1.0.

Docker-backed Python and shell execution has no runtime network access and no
silent host fallback. Without Docker or the required image, PLwC reports Safe
Mode and the sandbox operation fails closed while non-sandbox governed
functions remain available.

## 14. Verification status

The current r24 evidence records:

| Gate | Result |
| --- | --- |
| Installer Pester contracts | 69 passed, 0 failed, 0 skipped |
| Configuration integration tests | 13 passed |
| Browser extension suite | 173 passed |
| Store package reproducibility, inventory, identity and secret scan | PASS |
| r23-to-r24 installed update and shortcut acceptance | PASS |
| Installed Bridge build and tool contract | `plwc-chat-bridge@1.0.0`, 8 tools |
| Chrome and Edge Store-origin loopback health checks | PASS |
| Public r24 reviewer download and SHA-256 reproduction | PASS |
| Store-signed Chrome/Edge installation acceptance | PENDING external review/test channel |

The detailed evidence is
[`CHAT_BRIDGE_1_0_INSTALLER_R24_ACCEPTANCE_EN.md`](evidence/CHAT_BRIDGE_1_0_INSTALLER_R24_ACCEPTANCE_EN.md).

## 15. Distribution, signing and Store state

The public r24 GitHub release is marked as a pre-release. Its Setup executable
is deliberately unsigned after the Product Owner declined the commercial
signing route. Windows may therefore show an unknown-publisher warning. The
exact public URL and SHA-256 are the external integrity anchors for this
candidate.

The submitted Chrome and Edge candidates contain the 1.0 packages, public-safe
listing text, privacy declarations, support/privacy URLs and three sanitized
1280 x 800 screenshots. Chrome is private with a trusted tester and deferred
publication; Edge is hidden/link-only. Both are under review. Approval,
controlled availability and public publication remain separate gates.

## 16. Remaining release gates

Before any public Store publication:

1. wait for both submitted controlled tracks to complete review;
2. install the review-approved Store-signed package under its real ID;
3. repeat Native Messaging, loopback, tool-contract, confirmation, restart and
   missing-native-host acceptance;
4. compare the saved screenshots with the accepted Store-ID build;
5. renew the final H2 handoff binding Setup, Gateway, Bridge and Store
   identities.

The absence of Store review is an external sequencing hold, not evidence that
the locally tested 1.0 components failed.

## 17. Documentation map

- Windows end-user setup: [`WINDOWS_INSTALLER_GUIDE.md`](WINDOWS_INSTALLER_GUIDE.md)
- Full installation routes: [`INSTALLATION.md`](INSTALLATION.md)
- Configuration: [`CONFIGURATION.md`](CONFIGURATION.md)
- First run and onboarding: [`FIRST_RUN.md`](FIRST_RUN.md), [`ONBOARDING.md`](ONBOARDING.md)
- Tool reference: [`TOOLS.md`](TOOLS.md)
- Security and Safe Mode: [`SECURITY_MODEL.md`](SECURITY_MODEL.md), [`SAFE_MODE.md`](SAFE_MODE.md)
- Troubleshooting: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- Store submission gate: [`../integrations/plwc-chat-bridge/extension/store/submission-checklist.md`](../integrations/plwc-chat-bridge/extension/store/submission-checklist.md)

Historical rc and earlier installer evidence remains intentionally unchanged.
It records what was true for those exact artifacts and must not be relabeled as
1.0 evidence.
