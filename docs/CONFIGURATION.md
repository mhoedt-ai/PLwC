# Configuration

## security.yaml

The local policy file controls execution, safe mode, Docker behavior, allowed roots, protected paths, audit and governance rules.

Security-relevant configuration must not be modifiable through MCP tools during runtime.

## Runtime Defaults

If no local `security.yaml` exists, PLwC uses conservative local defaults:

- Windows workspace root: `%APPDATA%\PLwC\workspace`
- Windows profile root: `%APPDATA%\PLwC\profiles`
- Windows config root: `%APPDATA%\PLwC\config`
- macOS/Linux workspace root: `~/.plwc/workspace`
- macOS/Linux profile root: `~/.plwc/profiles`
- macOS/Linux config root: `~/.plwc/config`
- audit log: user-scoped PLwC log directory
- active profile name: `default`
- Docker image: `python:3.12-slim`
- Docker network: `none`
- memory write threshold: `2`
- persona write threshold: `3`

PLwC must not use the process current working directory or
`C:\Windows\System32` as a default workspace or profile root.

The MCPB extension settings can override the workspace root, profile root,
active profile name, optional security config file and memory/persona
thresholds.

Client configuration generation must expose only `plwc-gateway`.

## Workspace search scope guards (RC12-FS-003)

`plwc_workspace_operation(operation="search")` bounds its walk so a single large
binary (e.g. a multi-GB `.zip`) or a huge export tree cannot stall the gateway.
The guards only ever **reduce** scope — they never widen access.

Search skips:

- files larger than the per-file cap (stat-checked before opening);
- binary files — a NUL byte in the head probe window (8 KiB) marks the file binary;
- excluded directories: `qdrant_storage`, `.git`, `__pycache__`, `node_modules`.

A scan cap bounds how many files are content-scanned per search. Every search
result carries `search_stats` (`scanned_files`, `skipped_files`
`{too_large, binary, unreadable}`, `skipped_total`, `excluded_dirs`,
`max_file_bytes`, `max_files_scanned`, `truncated`, `result_limit_reached`) so a
search never silently passes over the file holding the answer.

| Env var (extension config) | Meaning | Default |
|---|---|---|
| `PLWC_WORKSPACE_SEARCH_MAX_FILE_BYTES` | Per-file size cap for text search | 5 MiB |
| `PLWC_WORKSPACE_SEARCH_MAX_FILES_SCANNED` | Max files content-scanned per search | 50000 |

Both must be positive integers; an invalid value falls back to the default with a
setup warning.

## Active Profile

The effective profile path is:

```text
profiles_path / active_profile_name
```

The active profile name must be a single directory name without path
separators. It defaults to `default`.

`setup_complete` is true only when:

- workspace and profiles paths exist;
- the active profile directory exists;
- required profile files are present;
- the profile runtime adapter is available.

## Profile governance config (`<profile>/governance/config.yaml`)

Per-profile, simple `key: value` lines. Thresholds must be integers ≥ 1 when
present; profile-local metadata can never enable direct workspace profile writes,
disable governed-tool requirements, or disable Governor confirmation.

| Key | Meaning | Default |
|---|---|---|
| `memory_write_threshold` / `persona_write_threshold` / `temperament_write_threshold` | Promotion evidence thresholds | 2 / 3 / 2 |
| `retirement_age_threshold_days` | `list_retirable` `history_only` age | 90 |
| `near_duplicate_similarity_threshold` | `list_retirable` `near_duplicate` (0–1; `0` disables) | 0.85 |
| `inner_redundancy_threshold` | `scan_tagebuch` `redundancy_warning` (0–1) | 0.85 |
| `qdrant_enabled` | Enable the Qdrant retrieval index | false |
| `persona_aliases` | Comma-separated persona self-reference name(s) | *(empty)* |
| `user_aliases` | Comma-separated user name(s) | *(empty)* |

## Profile compile extension setting

The packaged Claude Desktop extension setting `persona_layer_disabled` maps to
`PLWC_PERSONA_LAYER_DISABLED`.

| Key | Meaning | Default |
|---|---|---|
| `persona_layer_disabled` | Omit the `PERSONA` block from profile compile output by default | false |

This setting changes only the default compile output for
`plwc_profile(operation="compile")`. A per-call `persona_layer=true|false`
argument overrides the extension default for that single compile request. It
omits the `PERSONA` block and labelled role, identity, voice or working-context
lines from `CORE` when disabled. It does not mutate profile files, does not
change persona-promotion thresholds, does not disable hard gates and does not
change Governor confirmation.

Direct non-Desktop environments may still set the legacy
`PLWC_PERSONA_LAYER_ENABLED=false` environment variable. Packaged Claude Desktop
builds use the disable flag because the rc18.dev2 Desktop smoke showed that a
default-true Boolean did not reliably propagate `false`.

### Persona / user aliases and the INNER gate (RC12-GEN-001)

The INNER security gate does not hard-code any persona or user name. Names are
configuration:

- `persona_aliases` — the persona's own name(s). The gate additionally blocks
  **third-person self-claims** under these names (e.g. `"<persona> is conscious"`,
  `"<persona> feels sad"`). Alias values are `re.escape`'d and run through the same
  ASCII canonical space as the rest of the gate (no regex injection/bypass).
- `user_aliases` — the user's name(s). Recognized as user-insight / direct-instruction
  signals (the generic `"user …"` terms always apply regardless).

**Empty is allowed and explicit:** with no `persona_aliases`, the gate runs the
generic **first-person** checks only (e.g. `"I am alive"`, `"ich bin lebendig"`,
plus the autonomy/emotion/ontology hard gates) — there is **no name-based
(third-person) protection**, because there is no configured name to match. First-
person blocking is never weakened by an empty config.
