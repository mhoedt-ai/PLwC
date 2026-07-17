# PLwC v0.2.0-rc18.dev9 Open Beta Installation Guide

This guide covers the supported and planned client paths for the Dev 9 Open
Beta: Claude Desktop, maintainer-confirmed local GPT clients, local Odysseus and
hosted ChatGPT web/custom apps.

The current Open Beta artifact is unsigned. Verify the exact SHA256 before
installation:

```text
Package: plwc-gateway-0.2.0-rc18.dev9.mcpb
SHA256: 2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345
```

PLwC exposes exactly one public MCP server:

```text
plwc-gateway
```

Do not install separate PBA, PLfC, Desktop Commander, filesystem or Hardened
Commander MCP servers as part of PLwC.

## Client Support Matrix

| Client | Dev 9 status | Transport | Installation shape |
| --- | --- | --- | --- |
| Claude Desktop | Supported and smoke-tested | Local MCPB / stdio | Install the rc18.dev9 MCPB extension. |
| Local GPT client | Supported in the maintainer setup | Local stdio | Extract the rc18.dev9 package and register its bundled `server.py` as one MCP server. |
| Odysseus | Supported as an external local PoC and smoke-tested | Local stdio | Extract the rc18.dev9 package and configure its bundled `server.py` as one external MCP server. |
| ChatGPT web/custom app | Planned, not directly installable from the Dev 9 package | Remote MCP over HTTPS or Secure MCP Tunnel | Requires the future authenticated PLwC remote facade from `V1-REMOTE-MCP-FACADE-001`. Do not upload the MCPB or expose the raw local gateway. |

Claude Desktop, the maintainer's local GPT client and Odysseus use the existing
local gateway. Hosted ChatGPT web/custom apps are a different deployment class:
they connect through remote MCP infrastructure and do not directly install a
Claude Desktop MCPB.

A separate local browser-extension proof of concept is tracked as
`V1-LOCAL-CHATGPT-ADAPTER-001` under the working name **PLwC Chat Bridge**. It
connects ChatGPT web to a loopback bridge and then to the PLwC stdio gateway
without a public tunnel. It is proposed for the v0.2.0-rc19 development track,
is not a supported Dev 9 installation path yet and does not replace the hosted
remote-facade plan. See
[`LOCAL_CHATGPT_CLIENT_ADAPTER.md`](LOCAL_CHATGPT_CLIENT_ADAPTER.md).

## Requirements

Windows is the fully smoke-tested Open Beta target. The package manifest also
declares macOS and Linux with Python 3.11 or newer, but those platforms do not
have the same recorded Desktop evidence as Windows.

Common local requirements:

- Python `>=3.11`;
- the PLwC artifact: `plwc-gateway-0.2.0-rc18.dev9.mcpb`;
- separate workspace and profile directories;
- exactly one PLwC-related MCP server: `plwc-gateway`.

Client requirement:

- Claude Desktop with extension support for the MCPB route; or
- a local GPT host that can register a stdio MCP server; or
- an Odysseus build/runtime that can register a local stdio MCP server.

Required for Docker Mode and sandboxed Python/Shell execution:

- Docker Desktop;
- local sandbox image `python:3.12-slim`.

PLwC can run in Safe Mode without Docker. In Safe Mode, workspace and profile
tools remain policy-controlled, but sandboxed Python and shell execution fail
closed.

Profile onboarding can still complete in Safe Mode. Docker is required for
sandbox/document-worker operations, not for creating the first governed PLwC
profile.

## Verify The Open Beta Artifact

On Windows PowerShell:

```powershell
Get-FileHash .\plwc-gateway-0.2.0-rc18.dev9.mcpb -Algorithm SHA256
```

Expected hash:

```text
2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345
```

Stop if the hash differs. The package is unsigned, so exact hash verification
is the current integrity check.

## Install Python

Install Python 3.11 or newer and make sure it is available in `PATH`.

Verify:

```powershell
python --version
```

Expected:

```text
Python 3.11.x or newer
```

If the MCP client cannot find Python, restart the client after installing
Python and confirming `python --version` works in a new terminal.

## Install Docker Desktop

Install Docker Desktop and start it before starting the MCP client if sandbox
tools should work.

Verify:

```powershell
docker --version
docker info
```

`docker --version` only proves the CLI exists. `docker info` must also work,
because it proves that the Docker daemon is reachable.

## Prepare The Sandbox Image Manually

PLwC uses Docker with `--pull never`. It must not pull images implicitly at
runtime.

Prepare the image yourself:

```powershell
docker pull python:3.12-slim
docker image inspect python:3.12-slim
```

If the image is missing, sandbox execution fails closed. This is intended
security behavior.

## Install The PLwC MCPB In Claude Desktop

1. Open Claude Desktop.
2. Open Settings.
3. Open Extensions.
4. Open Advanced settings or the Extension Developer section if required.
5. Choose Install Extension.
6. Select `plwc-gateway-0.2.0-rc18.dev9.mcpb`.
7. Confirm installation.

After installation, Claude Desktop should show PLwC Gateway. No separate PBA,
PLfC, Desktop Commander or filesystem extension should be enabled for PLwC.

## Connect PLwC To A Local GPT Client Or Odysseus

The maintainer's local GPT setup and Odysseus both use the existing local
`plwc-gateway` stdio runtime. The MCPB is a Claude Desktop installation format,
so either local client must point to the bundled runtime inside an extracted
package directory.

### 1. Extract the verified package

Choose a dedicated local application directory outside the PLwC workspace and
profile roots. Then extract the package with Python:

```powershell
python -m zipfile -e .\plwc-gateway-0.2.0-rc18.dev9.mcpb .\plwc-gateway-0.2.0-rc18.dev9
```

The extracted directory must contain `server.py`, `src/`, `manifest.json` and
the public package resources. Keep the extracted directory read-only during
normal use.

### 2. Register one local stdio MCP server

Open the local GPT or Odysseus MCP server settings and create one external
server with these values. Field names may differ between clients and builds, so
map them by meaning:

| Field | Value |
| --- | --- |
| Name | `plwc-gateway` |
| Transport | `stdio` |
| Command on Windows | Absolute path to `python.exe` |
| Command on macOS/Linux | Absolute path to `python3` |
| Arguments | Absolute path to the extracted `server.py` |

Configure the runtime environment through the client MCP entry rather than
letting the model choose paths:

```text
PLWC_WORKSPACE_ROOT=<dedicated disposable workspace>
PLWC_PROFILE_ROOT=<separate profile directory>
PLWC_ACTIVE_PROFILE_NAME=default
PLWC_CONFIG_FILE=
PLWC_MEMORY_WRITE_THRESHOLD=2
PLWC_PERSONA_WRITE_THRESHOLD=3
PLWC_TEMPERAMENT_WRITE_THRESHOLD=2
PLWC_QDRANT_ENABLED=false
PLWC_PERSONA_LAYER_DISABLED=true
```

`PLWC_PERSONA_LAYER_DISABLED=true` is the conservative local-client default. It
omits persona identity and role steering from compiled context while keeping
hard gates, conscience, temperament, profile protection and Governor
confirmation active. Set it to `false` only after deciding that explicit,
inspectable persona context should be used.

Do not register raw PBA, Commander, filesystem or host-shell servers as part of
the PLwC integration. GPT- or Odysseus-native tools that bypass PLwC remain
outside the PLwC security boundary.

### 3. Add a local GPT or Odysseus system instruction

Use this instruction for an agent that should work through PLwC:

```text
Use plwc-gateway as the only MCP path for PLwC-managed workspaces, profiles, documents, reflection and memory governance. At session start, inspect plwc_status(scope="runtime") and plwc_describe(scope="tools"). Compile profile context only with an explicit persona_layer value and keep the result inspectable. Do not use client-native shell or filesystem mutation tools to bypass a PLwC denial. Never write protected profile or governance files through workspace tools. Persistent profile, memory, persona or temperament changes require a PLwC Governor plan, explicit user approval and confirmed apply.
```

### 4. Run the local stdio first-run checks

1. Start or reload the configured MCP server.
2. Confirm the runtime reports `0.2.0rc18.dev9` and server
   `plwc-gateway`.
3. Confirm exactly eight PLwC public tools are visible.
4. Call `plwc_status(scope="first_run")` and follow the returned next action.
5. Call `plwc_profile(operation="compile", compile_mode="boot",
   persona_layer=false)` for the conservative PoC path.
6. In a disposable workspace, test list/read and one bounded write.
7. Verify parent traversal and a protected profile write are denied without
   mutation.
8. Use `plwc_profile(operation="doctor", doctor_mode="clu")` only as a
   read-only diagnostic.
9. Do not call Governor `apply` without explicit user approval.

The recorded rc18.dev9 Odysseus smoke passed this boundary model, and the local
GPT stdio route is maintainer-confirmed. Both prove PLwC behavior only for calls
that actually pass through `plwc-gateway`.

## Hosted ChatGPT Web And Custom-App Status

The local GPT stdio route above is distinct from a hosted ChatGPT web/custom
app. The Dev 9 MCPB cannot be uploaded as a ChatGPT web app. Hosted ChatGPT
connects to remote MCP infrastructure; local or private servers require a
reachable HTTPS MCP endpoint or OpenAI Secure MCP Tunnel. The current PLwC
package exposes a local stdio server and does not yet implement the
authenticated remote facade required by `V1-REMOTE-MCP-FACADE-001`.

Therefore the current Open Beta instructions are:

- do not upload the `.mcpb` file to ChatGPT;
- do not point a public tunnel directly at the raw PLwC gateway;
- do not expose local workspace, profile or audit paths to a hosted service;
- do not treat ChatGPT permission prompts as a replacement for PLwC policy;
- wait for a release that explicitly implements and smoke-tests the PLwC remote
  facade.

The planned ChatGPT route is:

```text
ChatGPT
  -> authenticated HTTPS /mcp or Secure MCP Tunnel
  -> PLwC remote facade
  -> local plwc-gateway policy boundary
  -> governed adapters
```

The first remote slice is expected to be read-heavy: status, explicit context
bootstrap, bounded search/read and Governor plan preview. Confirmed apply,
sandbox execution and artifact creation remain deferred until authentication,
confirmation ownership, audit behavior and the remote threat model are tested.

When that facade exists, ChatGPT setup will use Developer Mode to create a
custom app, select the tunnel or provide the HTTPS `/mcp` endpoint, scan the
advertised tools and test the draft app before publication. See the official
[OpenAI ChatGPT connection guide](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt),
[Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
and [Developer Mode guidance](https://help.openai.com/en/articles/12584461).

## Configure PLwC Extension Fields

The MCPB extension exposes these fields:

- `workspace_path`
- `profiles_path`
- `active_profile_name`
- `security_config`
- `memory_write_threshold`
- `persona_write_threshold`
- `temperament_write_threshold`
- `qdrant_enabled`
- `persona_layer_disabled`

Recommended Windows example:

```text
workspace_path: C:\Users\<USER>\PLwC_Workspace
profiles_path: C:\Users\<USER>\AppData\Roaming\PLwC\profiles
active_profile_name: default
security_config: leave empty for defaults
memory_write_threshold: leave empty or 2
persona_write_threshold: leave empty or 3
temperament_write_threshold: leave empty or 2
qdrant_enabled: false
persona_layer_disabled: false
```

Optional security config path:

```text
C:\Users\<USER>\AppData\Roaming\PLwC\config\security.yaml
```

Important:

- `workspace_path` and `profiles_path` must be separate.
- `profiles_path` must be outside `workspace_path`.
- `workspace_path` must not contain profile, governance or config files.
- If `workspace_path` contains protected governance targets, PLwC fails closed
  with: `allowed root contains protected governance targets`.

## Required Project Instruction / System Prompt

Copy this into the Claude Desktop project instruction, user instructions or
equivalent system prompt for sessions where PLwC should govern the assistant:

```text
Use PLwC as the single visible local gateway for local files, profiles, documents and governance. Do not bypass PLwC with other local MCP tools for PLwC-managed files, profiles, documents or policy decisions.

At the beginning of each new PLwC session, search and activate PLwC tools with tool_search("plwc") if they are not visible. Then call plwc_status with scope="first_run" and show the user the relevant status: PLwC runtime, profile/onboarding, workspace, profile root, Docker, document-worker readiness, Safe Mode and next action. Then call plwc_profile with operation="compile" and compile_mode="boot" when a profile is available. Use the returned compiled_layer as the binding working context for this session: role, name, tone, working style, initiative brake, memory rules, confirmation boundaries, governance rules and retrieval guidance. Use compile_mode="working" with task_context for bounded task-specific context; use compile_mode="full" only for audit or diagnosis.

If plwc_profile operation="compile" reports onboarding_required or onboarding_pending, tell the user: "Standard profile loaded. Onboarding is pending. Should I start the PLwC onboarding?"

If the user agrees, use only the PLwC-provided profile_onboarding_questions and profile_onboarding_schema. Do not invent additional project-specific onboarding questions and do not guess onboarding_answers keys. Ask the questions one by one. While collecting answers, say "Antwort notiert" or "Für den Profilplan aufgenommen", not "Gespeichert".

Create a profile plan with plwc_governor operation="plan" using the canonical onboarding_answers keys from profile_onboarding_schema. Show decision, unknown_fields, missing_required_fields, suggested_mappings, alias_mappings_applied, normalized_onboarding_answers, file_previews and planned writes. If decision is needs_correction or rejected, ask for corrected canonical fields and do not apply. Wait for explicit user approval. Only then call plwc_governor operation="apply" with confirmed=true. After successful apply, call plwc_profile operation="compile" with compile_mode="boot" again and immediately treat the returned compiled_layer as active session context.

If the user asks to switch profiles, list available profiles through PLwC profile/status tools, show the active profile, and use the governed profile_activation flow through plwc_governor operation="plan" and plwc_governor operation="apply" with confirmed=true. Do not tell the user to blindly type profile names into the extension config unless no governed activation flow is available.

Never modify profile, memory, reflection, or governance files through workspace tools. Use only PLwC governed facade tools such as plwc_governor and plwc_reflection.

Do not manually edit CORE.md, PERSONA.md, TEMPERAMENT.md, memory.md, reflection.md, journal.md, active_profile.json, compiled_prompt.txt or governance/config.yaml during normal onboarding. Direct edits to those files are admin repair outside the normal user flow.

If PLwC denies an action, treat that as an intended safety decision. Explain the reason and the safe next step instead of trying a different local MCP tool.

A normal chat command does not disable the active PLwC profile. To disable PLwC, the user must disable the PLwC extension/MCP in Claude Desktop.
```

German concise variant:

```text
Nutze PLwC als einziges lokales Gateway fuer lokale Dateien, Profile, Dokumente und Governance. Pruefe zu Beginn einer PLwC-Sitzung den PLwC-Status. Aenderungen an Persoenlichkeit, Erinnerung, Profilen und Governance duerfen nur ueber PLwC-Governor-/Onboarding-Flows erfolgen, nicht ueber direkte Dateiaenderungen. Wenn PLwC eine Aktion ablehnt, behandle das als Sicherheitsentscheidung und erklaere dem Nutzer den Grund sowie den sicheren naechsten Schritt.
```

## Claude Desktop First-Run Checklist

1. Install Python 3.11 or newer.
2. Install Docker Desktop.
3. Pull `python:3.12-slim` manually.
4. Install the MCPB in Claude Desktop.
5. Set `workspace_path`.
6. Set `profiles_path`.
7. Set `active_profile_name` or keep `default`.
8. Add the Project Instruction/System Prompt above.
9. Restart Claude Desktop.
10. Start a new chat.
11. Run `tool_search("plwc")` if PLwC tools are deferred.
12. Run `plwc_status(scope="first_run")`.
13. If onboarding is pending, create the first profile through
    `plwc_governor(operation="plan")` and
    `plwc_governor(operation="apply", confirmed=true)`.
14. Run `plwc_profile(operation="compile", compile_mode="boot")`.
15. Run `plwc_status(scope="sandbox")`.
16. Run a Python sandbox smoke test if Docker Mode is ready.

Expected first-run status fields include:

```text
setup_complete
onboarding_pending
active_profile_name
workspace_root
profile_root
docker_status
docker_message
docker_version
document_worker_available
safe_mode
missing_requirements
next_actions
greeting_message
claude_user_system_prompt_required
claude_user_system_prompt_text
```

Example greeting shape:

```text
PLwC ist aktiv. Profil: noch nicht eingerichtet. Docker: nicht gefunden / bereit. Dokumentfunktionen: bereit / eingeschraenkt. Naechster Schritt: Profil anlegen.
```

If Docker is missing, first-run status should say that document-worker/sandbox
operations may be unavailable until Docker is installed or running, and should
tell the user to install/start Docker Desktop and rerun PLwC status. It must not
block profile onboarding solely because Docker is absent.

## Profile Selection Through Chat

Claude Desktop MCPB user configuration cannot be assumed to support dynamic
profile dropdowns or buttons in the Dev 9 Open Beta. The `active_profile_name` field may
remain a text field, but users do not need to type profile directory names
blindly.

Supported chat flow:

```text
User: Welche Profile gibt es?
Assistant: Available profiles: [active] default, John Doe, Test123. Which profile should be activated?
User: Aktiviere Test123.
Assistant: I will prepare a governed profile activation plan.
```

Then PLwC must:

1. call `plwc_governor(operation="plan")` with
   `plan_type: profile_activation`;
2. show the validation result, preview and planned state change;
3. wait for explicit confirmation;
4. call `plwc_governor(operation="apply")` with
   `plan_type: profile_activation` and `confirmed: true`;
5. call `plwc_profile(operation="compile", compile_mode="boot")` so the
   selected profile becomes the active session context.

Profile activation writes only PLwC-owned active-profile state. It does not edit
Claude Desktop extension config.

## Troubleshooting

Symptom: only a few PLwC tools are visible.

Fix: run `tool_search("plwc")`.

Symptom: `allowed root contains protected governance targets`.

Cause: `workspace_path` contains profile, governance or config files.

Fix: move `profiles_path` outside `workspace_path`, or set `workspace_path` to a
dedicated project folder.

Symptom: Docker unavailable or Safe Mode.

Fix: start Docker Desktop, restart Claude Desktop if needed, then verify:

```powershell
docker --version
docker info
```

If `docker --version` works but `docker info` fails, Docker is installed but
the daemon is not running. Start Docker Desktop, then rerun
`plwc_status(scope="first_run")`.

Symptom: Docker image missing.

Fix:

```powershell
docker pull python:3.12-slim
```

Symptom: `setup_complete` is false.

Cause: onboarding is pending or the profile runtime is not ready.

Fix: run `plwc_status(scope="first_run")` and follow `next_action`.

Symptom: assistant tells you to edit `CORE.md`, `PERSONA.md`,
`TEMPERAMENT.md`, `memory.md` or `governance/config.yaml` by hand during
normal onboarding.

Fix: stop that flow. Use `plwc_governor(operation="plan")` and
`plwc_governor(operation="apply", confirmed=true)`. Normal workspace/document
tools are not allowed to write protected PLwC profile/governance files.

Symptom: assistant says "Gespeichert" while collecting onboarding answers.

Fix: this is wrong wording before governed apply. The assistant should say
"Antwort notiert" or "Für den Profilplan aufgenommen" until
`plwc_governor(operation="apply", confirmed=true)` succeeds.

Symptom: profile name typed manually but profile not found.

Fix: ask PLwC to list available profiles and activate one through the governed
chat flow.

Symptom: Claude Desktop UI labels differ from this guide.

Fix: use the Extensions or Advanced/Developer extension area that installs an
`.mcpb` file. After installation, start a new chat and run
`plwc_status(scope="first_run")` to verify the actual state.

Symptom: installing any `.mcpb` (or folder) fails with
`handleDxtFile: reply was never sent`, even for known-good files; a full quit
and reboot do not help.

Cause: the Claude Desktop installer dialog is broken in app version
`1.12603.1` — it rejects every extension package, not just PLwC.

Fix: register PLwC as a **direct MCP connector** instead of installing the
package. While Claude Desktop is **fully closed**, add a `mcpServers` entry to
`claude_desktop_config.json` pointing at your system Python and the bundled
`server.py` (e.g. under `%APPDATA%\PLwC\app\gateway-<version>`):

```jsonc
"mcpServers": {
  "PLwC Gateway": {
    "command": "C:\\Path\\to\\python.exe",
    "args": ["C:\\Users\\<you>\\AppData\\Roaming\\PLwC\\app\\gateway-<version>\\server.py"]
  }
}
```

The connector then appears under **Konnektoren**, not **Erweiterungen**. The
`.mcpb` SHA-256 in `MCPB_PACKAGING.md` stays the authoritative integrity check.
Switch back to a regular package install once a Desktop update fixes the
dialog.

Symptom: an edit to `claude_desktop_config.json` (e.g. switching the active
profile or connector path) is lost after restarting Claude Desktop.

Cause: Claude Desktop rewrites the config from its in-memory copy on its
lifecycle, clobbering edits made while it was running.

Fix: edit `claude_desktop_config.json` only **while Claude Desktop is fully
closed**, then start it.
