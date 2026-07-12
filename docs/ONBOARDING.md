# PLwC Onboarding

## 0.2.0-dev Facade Update

The `0.2.0-dev` public MCP boundary uses eight facade tools. Onboarding status
is reached through `plwc_status(scope="first_run")`; profile status and compile
through `plwc_profile(operation="status|snapshot|compile")`; profile creation,
activation, import, memory/persona promotion and reflection condensation through
`plwc_governor(operation="plan|apply")`; reflection writes through
`plwc_reflection(operation="write")`.

The previous individual public tool names such as `plwc_first_run_status`,
`plwc_profile_status`, `plwc_compile_profile`, `plwc_governor_plan`,
`plwc_governor_apply` and `plwc_write_reflection` are historical `0.1.0`
public names and are no longer exposed publicly on this branch. Internal
handlers may still exist for regression coverage. The 19-to-8 change is a
facade refactor, not Office Creation V2 and not release readiness.

PLwC Gateway installs as one MCP server:

```text
plwc-gateway
```

Do not install separate PBA, PLfC, Desktop Commander, filesystem or Hardened
Commander MCP servers as part of PLwC.

## Extension Settings

The MCPB package exposes these Claude Desktop extension settings:

- PLwC workspace path
- PLwC profiles path
- active PLwC profile name
- optional PLwC security config path
- memory write threshold
- persona write threshold

If the path fields are empty, PLwC uses safe user-scoped defaults.

Windows defaults:

```text
%APPDATA%\PLwC\workspace
%APPDATA%\PLwC\profiles
%APPDATA%\PLwC\config
```

macOS/Linux defaults:

```text
~/.plwc/workspace
~/.plwc/profiles
~/.plwc/config
```

PLwC must never default to `C:\Windows\System32`, the process current working
directory or an arbitrary launch directory.

## Workspace Path

Choose a normal project or notes directory owned by the current user. Do not use
drive roots, the home directory itself, system directories, Source A, Source B
or directories that contain protected governance files.

Workspace tools can read, write, list and search inside the configured
workspace root. Attempts outside that root are denied.

## Profiles Path

Choose a directory for PLwC profile data. The profile/governor/reflection tools
are exposed through `plwc-gateway`; they do not require a separate visible PBA
MCP server.

If profile setup is incomplete or the internal profile adapter is unavailable,
profile tools remain callable and return a clear setup-required or unavailable
response.

The active profile name defaults to:

```text
default
```

The active profile directory is:

```text
profiles_path / active_profile_name
```

Examples:

```text
%APPDATA%\PLwC\profiles\default
%APPDATA%\PLwC\profiles\Harald
```

Required profile files:

```text
CORE.md
PERSONA.md
TEMPERAMENT.md
memory.md
reflection.md
governance/config.yaml
```

Optional profile files created by the bundled template:

```text
journal.md
```

`journal.md` is used for governed profile history. It is not required for
profile readiness, but profile creation includes it so governed apply operations
have a local journal target.

If the active profile does not exist, `plwc_status(scope="first_run")` reports
`setup_complete: false`. If the active profile name came from Claude Desktop
settings or `security.yaml`, PLwC treats that name as the intended onboarding
target and does not fall back to another existing profile or stale
`active_profile.json` state. `plwc_profile(operation="status")` reports the
profiles path, configured active profile, resolved active profile,
`active_profile_source`, `active_state_profile`, `mismatch_reason`, onboarding
target profile, source, profile existence/validity, required files, missing
files, available profiles, onboarding questions and the next action.

## First-Run Status

If PLwC tools are deferred or not visible at the beginning of a Claude Desktop
conversation, the assistant should search for them with `tool_search("plwc")`
and then call `plwc_status(scope="first_run")`.

At the start of an installation or onboarding conversation, Claude should call
`plwc_status(scope="first_run")` before asking the user to edit anything. The
payload is safe to display as a greeting and includes:

- PLwC runtime status;
- active profile status and onboarding pending/complete state;
- `workspace_root` and `profile_root`;
- Docker CLI/daemon/version status;
- `docker_message` with clear missing/not-running/running guidance;
- Python status when available;
- document-worker readiness;
- Safe Mode status;
- `missing_requirements`, `next_action` and `next_actions`;
- `greeting_message`;
- Claude Desktop user-system-prompt guidance.

The status message distinguishes these Docker states:

```text
running
missing
daemon_not_running
disabled
unknown
```

If Docker is missing, PLwC must not crash and must not claim document or
sandbox operations are ready. The user-facing guidance is:

```text
Docker not detected. Document-worker/sandbox operations may be unavailable until Docker is installed/running.
Install/start Docker Desktop, then rerun PLwC status.
```

If Docker is installed but the daemon is not reachable, the next action is:

```text
Start Docker Desktop, then rerun PLwC status.
```

Profile onboarding remains possible in Safe Mode; Docker is required only for
sandbox/document-worker operations.

## Bootstrap Profile

When `profiles_path` exists but `active_profile_name` does not, PLwC creates a
minimal valid bootstrap profile only for the non-configured default/bootstrap
case. If the user has explicitly configured a new active profile name, PLwC
does not create a silent bootstrap and does not load an older valid profile.
Instead, the missing configured profile remains the onboarding target. The
default active profile name is:

```text
default
```

The bootstrap profile is intentionally neutral and safe:

- it contains every required profile file;
- it may include the optional governed `journal.md`;
- it does not contain user-specific assumptions;
- it marks onboarding as pending and incomplete;
- it can be loaded and compiled by `plwc_profile(operation="compile")`;
- it returns this startup message:

```text
Standard profile loaded. Onboarding is pending. Ask the user whether to start onboarding.
```

With a bootstrap profile, `plwc_status(scope="first_run")` reports:

```text
active_profile_exists: true
profile_runtime_available: true
onboarding_required: true
onboarding_complete: false
setup_complete: false
```

With an explicitly configured but missing active profile such as `ExampleProfile`,
`plwc_status(scope="first_run")` and `plwc_profile(operation="status")`
report:

```text
configured_active_profile: ExampleProfile
resolved_active_profile: ExampleProfile
onboarding_target_profile: ExampleProfile
profile_exists: false
profile_valid: false
status: onboarding_required
```

The governed onboarding plan defaults to that configured profile name when no
other profile is supplied. A confirmed apply creates that profile through the
PLwC-owned onboarding path; normal users should not manually edit protected
profile or governance files to create it.

Claude should use `profile_onboarding_questions` and
`profile_onboarding_schema` returned by PLwC. It must not invent a separate
question set or guess payload keys.

The user answers the onboarding questions. The assistant may ask them one by
one, but the assistant must use PLwC-provided questions and must not invent
project-specific questions unless the user explicitly asks for them.

During question collection, assistants must not imply that profile content has
already been written. For German sessions, prefer wording such as:

```text
Antwort notiert.
Für den Profilplan aufgenommen.
```

Only after `plwc_governor(operation="apply", confirmed=true)` succeeds may the
assistant say that profile content was saved. This avoids confusing temporary
answer collection with governed profile writes.

After `plwc_profile(operation="compile", compile_mode="boot")` succeeds, the
returned `compiled_layer` becomes the active session context immediately. Use
`compile_mode="working"` with `task_context` for bounded task-specific context,
and reserve `compile_mode="full"` for audit or diagnosis.

Profile creation is controlled by PLwC:

- `plwc_governor(operation="plan")` supports
  `plan_type: "profile_creation"` for governed first-profile or onboarding
  profile creation;
- `create_profile` and `onboarding_profile_creation` are accepted aliases, but
  `profile_creation` is the canonical plan type to prefer;
- `plwc_governor(operation="plan")` returns a profile-creation plan when the
  active profile is missing or the current bootstrap profile still has
  onboarding pending;
- the plan accepts structured answers to the onboarding questions and shows
  exactly which files will receive generated content;
- the plan always keeps `confirmation_required: true`;
- `plwc_governor(operation="apply")` creates a new profile only when called
  with `plan_type: "profile_creation"`, `confirmed: true` and the same
  onboarding answers;
- if no configured active profile overrides PLwC state and PLwC active-profile
  state is available, onboarding apply writes the active profile state itself;
- if Claude Desktop settings or `security.yaml` still select a different active
  profile, onboarding apply creates the requested profile files but reports
  `configured_active_profile_takes_precedence`, does not claim effective
  activation and tells the caller to update the configured active profile;
- existing profile files are not silently overwritten;
- bootstrap files may be replaced only by the confirmed onboarding apply;
- profile files are written only inside the PLwC-owned `profiles_path`;
- normal workspace/document tools remain unable to write protected profile or
  governance files.

Do not tell the user to manually edit these files during normal onboarding:

```text
CORE.md
PERSONA.md
TEMPERAMENT.md
memory.md
reflection.md
journal.md
governance/config.yaml
active_profile.json
compiled_prompt.txt
```

Minimum guided onboarding questions:

- Profile name
- Intended role/use case of the profile
- Preferred name
- Preferred form of address
- Preferred tone
- Preferred working style
- How strict the assistant should be
- What may be stored in memory
- What must never be changed without confirmation
- Main project/work context if any
- Language preference

Canonical structured answer keys:

```text
profile_name
role_use_case
preferred_name
form_of_address
tone
working_style
strictness
memory_scope
confirmation_boundaries
project_context
language_preference
special_instructions
```

Required keys:

```text
profile_name
role_use_case
preferred_name
form_of_address
tone
working_style
strictness
memory_scope
confirmation_boundaries
project_context
language_preference
```

Optional keys:

```text
special_instructions
```

Supported aliases are intentional and are reported in
`alias_mappings_applied`:

| Alias | Canonical key |
| --- | --- |
| `assistant_name` | `preferred_name` |
| `main_project` | `project_context` |
| `language` | `language_preference` |
| `confirmation_policy` | `confirmation_boundaries` |
| `memory_policy` | `memory_scope` |

Example payload:

```json
{
  "profile_name": "Harald",
  "preferred_name": "Mirco",
  "form_of_address": "Use Mirco",
  "role_use_case": "Technical work assistant and development companion",
  "project_context": "PLwC release hardening and MCPB validation",
  "tone": "Factual, direct, occasionally humorous",
  "working_style": "Structured, reviewing, no false promises",
  "strictness": "Security before convenience and traceability before speed",
  "memory_scope": "Only long-term useful information explicitly confirmed by the user",
  "confirmation_boundaries": "Never change persona, memory, policy or release decisions without confirmation",
  "language_preference": "German for status reports, English for code and public docs",
  "special_instructions": "Optional explicit user-provided profile instructions"
}
```

`plwc_governor(operation="plan")` validates onboarding payloads strictly. It returns
`accepted_fields`, `unknown_fields`, `missing_required_fields`,
`suggested_mappings`, `alias_mappings_applied`,
`normalized_onboarding_answers`, `target_profile`, `file_previews`,
`onboarding_complete_after_apply` and `decision`.

Generated profile file placement:

- `CORE.md` contains the profile name and hard operating principles only.
- `PERSONA.md` contains `role_use_case`, `project_context`, address,
  language preference, memory rules, confirmation boundaries and optional
  special instructions.
- `TEMPERAMENT.md` contains tone, working style, strictness and related
  behavioral preferences.

Persona-disabled onboarding:

- When the effective persona layer is disabled, `role_use_case`,
  `preferred_name`, `form_of_address` and `project_context` are inactive.
- Inactive persona-only fields are not shown in `profile_onboarding_questions`
  and are not listed in `required_fields`.
- They remain accepted for explicit callers and, if supplied, are stored in
  `PERSONA.md` for later persona-enabled use.

Recommended plan/apply shape:

```json
{
  "plan_type": "profile_creation",
  "onboarding_answers": {
    "profile_name": "ExampleProfile",
    "preferred_name": "Example User",
    "form_of_address": "Use Example User",
    "role_use_case": "Personal PLwC profile",
    "project_context": "Personal work context",
    "tone": "Clear and respectful",
    "working_style": "Structured and careful",
    "strictness": "Confirm protected profile changes",
    "memory_scope": "Only explicitly confirmed durable preferences",
    "confirmation_boundaries": "Confirm profile, memory, persona and governance changes",
    "language_preference": "German for chat, English for public docs"
  }
}
```

If `decision` is `needs_correction` or `rejected`, the assistant must ask for
the corrected canonical fields and rerun the plan.
`plwc_governor(operation="apply")` blocks mutation for incomplete or invalid
onboarding plans, even when `confirmed=true`. Unknown keys are never silently
dropped.

Answer mapping:

| Target file | Onboarding answers used |
| --- | --- |
| `CORE.md` | `role_use_case`, `project_context` |
| `PERSONA.md` | `preferred_name`, `form_of_address`, `memory_scope`, `confirmation_boundaries`, `language_preference`, `special_instructions` |
| `TEMPERAMENT.md` | `tone`, `working_style`, `strictness`, `language_preference`, `special_instructions` |
| `memory.md` | `memory_scope` as storage policy only; no arbitrary memories are invented |
| `reflection.md` | header only; no fake reflection history is invented |
| `governance/config.yaml` | active thresholds, confirmation requirements, protected files and write boundaries |
| `journal.md` | governed profile creation record |

Empty answers use conservative placeholders instead of invented facts. Memory
and persona thresholds come from PLwC configuration or extension settings, not
from arbitrary user prompts.

Importing existing profiles such as Harald from Source A is a future/manual
path. The release-safe direction is to import or copy the external profile into
the PLwC-owned profiles path and then work on the PLwC copy. PLwC must not use
Source A profiles directly as release runtime state.

## Profile Activation

Only one profile can be active. Profile activation is not a multi-select
checkbox concept.

Claude Desktop MCPB extension settings cannot be assumed to provide dynamic
dropdowns or buttons in v0.1.0. The `active_profile_name` extension field may
remain a text field, but the supported user flow is governed chat-based
activation:

1. The user asks which profiles exist.
2. The assistant calls PLwC profile/status tools.
3. PLwC reports `available_profiles`, marks the active profile and reports
   `active_profile_source`.
4. The user selects one profile by name or number.
5. The assistant calls `plwc_governor(operation="plan")` with
   `plan_type: profile_activation`.
6. The assistant shows validation and the planned state change.
7. The user confirms.
8. The assistant calls `plwc_governor(operation="apply")` with
   `plan_type: profile_activation` and `confirmed: true`.
9. The assistant calls `plwc_profile(operation="compile", compile_mode="boot")`
   and uses the returned `compiled_layer`.

Profile activation writes PLwC-owned active-profile state, for example
`active_profile.json` below the PLwC config root. It does not edit Claude
Desktop config. Status reports the source as one of:

```text
default
extension_config
security_config
plwc_state
```

Workspace tools cannot modify profile or governance files and must not be used
for profile activation.

## Project Instruction / System Prompt

Use this instruction block in Claude Desktop projects that should be governed by
PLwC:

```text
Use PLwC as the single visible local gateway for local files, profiles, documents and governance. Do not bypass PLwC with other local MCP tools for PLwC-managed files, profiles, documents or policy decisions.

At the beginning of each new PLwC session, search and activate PLwC tools with tool_search("plwc") if they are not visible. Then call plwc_status with scope="first_run" and show the user the relevant status: PLwC runtime, profile/onboarding, workspace, profile root, Docker, document-worker readiness, Safe Mode and next action. Then call plwc_profile with operation="compile" and compile_mode="boot" when a profile is available. Use the returned compiled_layer as the binding working context for this session: role, name, tone, working style, initiative brake, memory rules, confirmation boundaries, governance rules and retrieval guidance. Use compile_mode="working" with task_context for bounded task-specific context; use compile_mode="full" only for audit or diagnosis.

If plwc_profile operation="compile" reports onboarding_required or onboarding_pending, tell the user: "Standard profile loaded. Onboarding is pending. Should I start the PLwC onboarding?"

If the user agrees, use only the PLwC-provided profile_onboarding_questions. Do not invent additional project-specific onboarding questions. Ask the questions one by one. While collecting answers, say "Antwort notiert" or "Für den Profilplan aufgenommen", not "Gespeichert".

Create a profile plan with plwc_governor operation="plan" using the user's onboarding_answers. Show file_previews and planned writes. Wait for explicit user approval. Only then call plwc_governor operation="apply" with confirmed=true. After successful apply, call plwc_profile operation="compile" with compile_mode="boot" again and immediately treat the returned compiled_layer as active session context.

If the user asks to switch profiles, list available profiles through PLwC profile/status tools, show the active profile, and use the governed profile_activation flow through plwc_governor operation="plan" and plwc_governor operation="apply" confirmed=true. Do not tell the user to blindly type profile names into the extension config unless no governed activation flow is available.

Never modify profile, memory, reflection, or governance files through workspace tools. Use only PLwC governed facades such as plwc_governor operation="plan|apply" and plwc_reflection operation="write".

Do not manually edit CORE.md, PERSONA.md, TEMPERAMENT.md, memory.md, reflection.md, journal.md, active_profile.json, compiled_prompt.txt or governance/config.yaml during normal onboarding. Direct edits to those files are admin repair outside the normal user flow.

If PLwC denies an action, treat that as an intended safety decision. Explain the reason and the safe next step instead of trying a different local MCP tool.

A normal chat command does not disable the active PLwC profile. To disable PLwC, the user must disable the PLwC extension/MCP in Claude Desktop.
```

German concise variant for Claude Desktop user/system instructions:

```text
Nutze PLwC als einziges lokales Gateway fuer lokale Dateien, Profile, Dokumente und Governance. Pruefe zu Beginn einer PLwC-Sitzung den PLwC-Status. Aenderungen an Persoenlichkeit, Erinnerung, Profilen und Governance duerfen nur ueber PLwC-Governor-/Onboarding-Flows erfolgen, nicht ueber direkte Dateiaenderungen. Wenn PLwC eine Aktion ablehnt, behandle das als Sicherheitsentscheidung und erklaere dem Nutzer den Grund sowie den sicheren naechsten Schritt.
```

English concise variant:

```text
Use PLwC as the single visible local gateway for local files, profiles, documents and governance. Check PLwC status at the start of every PLwC session. Use governed flows for profile, memory, persona and governance changes: PLwC Governor or onboarding flows, not direct file edits. If PLwC denies an action, treat that as an intended safety decision and explain the reason plus the safe next step.
```

After a profile exists with all required files, PLwC uses its internal profile
runtime by default. Explicit Source A adapter contract tests remain available
for development, but a clean MCPB install does not require a separate visible
PBA MCP server or a Source A checkout.

## Protected Files

Ordinary workspace tools cannot write protected governance or policy files,
including:

```text
CORE.md
PERSONA.md
TEMPERAMENT.md
CONSCIENCE.md
memory.md
reflection.md
journal.md
compiled_prompt.txt
security.yaml
config/*.yaml
```

Use governed PLwC profile tools for reflection and governor writes.

The only normal onboarding path that writes protected profile files is
`plwc_governor(operation="apply")` for a validated profile-creation plan with
`confirmed=true`. That path validates the profile name, keeps writes inside the
PLwC profiles root, generates safe governance defaults, writes journal/setup
evidence and updates PLwC active profile state when configured.

An onboarding smoke confirmed this intended flow with configured active profile
`ExampleProfile`: the profile did not exist, PLwC kept `ExampleProfile` as the
onboarding target instead of falling back to `default`,
guided onboarding used `plan_type=profile_creation`, confirmed apply created
seven profile files, active profile state was set to `ExampleProfile`, and
`plwc_profile(operation="compile", compile_mode="boot")` loaded
`ExampleProfile` without manual AppData edits.

## Safe Mode

Safe Mode means Docker sandbox execution is unavailable. Workspace and
profile-safe operations remain policy-controlled, but code execution tools fail
closed.

PLwC does not install Python or Docker automatically. PLwC does not fall back to
host shell execution.

## Docker Mode

Docker Mode requires:

- Python 3.11 or newer visible to Claude Desktop;
- Docker Desktop or Docker Engine installed and running;
- the configured sandbox image available locally;
- Docker image pulls prepared manually before runtime.

PLwC runtime execution uses server-owned Docker arguments, `--network none`,
`--pull never`, a read-only root filesystem, a tmpfs `/tmp`, dropped
capabilities, no-new-privileges, a non-root user and exactly one workspace mount
to `/work`.

PLwC does not auto-pull Docker images unless a future policy explicitly
documents and allows it.

`plwc_sandbox_status` reports Python availability, Python executable/version,
Docker CLI availability, Docker executable/version, Docker daemon reachability,
configured sandbox image, whether the image exists locally, whether pulls are
disabled, workspace mount readiness, audit log writability, final sandbox
readiness and next actions. These diagnostics are reported independently so a
mount-policy failure does not hide Docker or Python status.

Common causes for unavailable Docker Mode:

- Claude Desktop was started before Docker Desktop;
- `docker` is not visible in the Claude Desktop extension PATH;
- Docker daemon is not reachable;
- the configured image is missing locally and runtime pulls are disabled;
- the configured workspace mount was rejected;
- the audit log path is not writable.

## If Onboarding Fails

Do not fall back to manual edits of protected profile/governance files. Instead:

1. Call `plwc_status(scope="first_run")`.
2. Read `missing_requirements`, `next_action` and `next_actions`.
3. If paths are wrong, fix the Claude Desktop extension fields and restart.
4. If Docker is missing, continue profile onboarding in Safe Mode and install
   or start Docker later for document/sandbox operations.
5. If the profile schema is invalid, treat it as an admin repair case outside
   normal onboarding and keep the protected-file boundary intact.

Claude Desktop UI labels for extension installation vary across versions. If
the household UI does not show exactly the labels in this guide, use the
Extensions or Advanced/Developer extension area that installs an `.mcpb` file,
then rerun `plwc_status(scope="first_run")`.

## Governance Thresholds

Memory and persona thresholds control how much evidence is required before PLwC
is willing to propose or apply memory/persona changes.

Defaults:

```text
memory write threshold: 2
persona write threshold: 3
```

Lower values make PLwC more willing to propose or write memory/persona changes.
Invalid configured values are ignored in favor of safe defaults with a clear
status warning.

Normal MCP tools cannot silently lower these thresholds at runtime. Changes must
come from local configuration or extension settings and remain visible in
status output.

## Deferred Tool Discovery

Claude Desktop may defer some installed MCP tools. If PLwC profile, governor or
reflection tools are not immediately visible at session start, search for them:

```text
tool_search("plwc")
```

Deferred tools are not a second MCP server and are not a PLwC bypass. PLwC still
exposes exactly one public server: `plwc-gateway`.

PLwC does not automatically write Claude Project Instructions or other external
client configuration without explicit user action. Copy any suggested
instruction text manually if a project wants that behavior.
