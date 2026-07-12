# First Run

## 0.2.0-dev Facade Note

For `0.2.0-dev`, first-run discovery is exposed through
`plwc_status(scope="first_run")`. The previous public tool
`plwc_first_run_status` is historical `0.1.0` evidence and is no longer a
public MCP tool on this branch.

Profile creation and activation still use governed plan/apply semantics, now
through `plwc_governor(operation="plan")` and
`plwc_governor(operation="apply")`. Profile compilation is reachable through
`plwc_profile(operation="compile")`. Normal workspace/document operations must
not manually write protected profile or governance files.

The first run should guide users through:

1. If PLwC tools are deferred or not visible yet, search for them with
   `tool_search("plwc")`.
2. Call `plwc_status(scope="first_run")`.
3. Show the `greeting_message`.
4. Check workspace and profile roots.
5. Check active profile and onboarding pending/complete state.
6. Check Docker CLI, Docker daemon and document-worker readiness.
7. Explain Safe Mode when Docker is missing or not running.
8. Provide the Claude Desktop user-system-prompt guidance.
9. Read `profile_onboarding_schema` from `plwc_status(scope="first_run")` or
   `plwc_describe(scope="profiles")` and use only canonical onboarding keys.
10. Create the first profile only through `plwc_governor(operation="plan")` and
   `plwc_governor(operation="apply")` with `plan_type=profile_creation` and
   `confirmed=true`.
11. Compile the active profile.
12. Run sandbox/document-worker checks only when Docker is ready.

Basic setup should not require manual JSON or YAML editing.

If Claude Desktop or `security.yaml` explicitly configures an active profile
name, that name is authoritative. A missing configured profile returns
`status: onboarding_required` with `onboarding_target_profile` set to the
configured name. PLwC must not silently load another existing profile or the
last PLwC active-profile state in that case.

Status payloads expose `configured_active_profile`, `resolved_active_profile`,
`active_profile_source`, `active_state_profile`, `profile_exists`,
`profile_valid`, `available_profiles`, `mismatch_reason` and `next_actions`
where applicable. If `active_profile.json` points at another valid profile but
a configured profile is present, `mismatch_reason` reports that the configured
profile takes precedence.

The same precedence applies after governed profile creation. If a caller creates
profile `NewProfile` while Claude Desktop extension config still selects another
profile such as `ExistingProfile`, apply creates the new profile files but must report
that effective activation is blocked by the configured active profile. The
caller should update the extension-configured active profile, reload or restart
Claude Desktop, then rerun `plwc_status(scope="runtime")`.

The canonical governed profile creation plan type is `profile_creation`.
`create_profile` and `onboarding_profile_creation` are accepted aliases for
compatibility, but docs and prompts should prefer `profile_creation`.

Normal onboarding must not require or suggest direct edits to `CORE.md`,
`PERSONA.md`, `TEMPERAMENT.md`, `memory.md`, `reflection.md`, `journal.md`,
`active_profile.json`, `compiled_prompt.txt` or `governance/config.yaml`.

Onboarding apply is all-or-nothing. If `plwc_governor(operation="plan")` reports
`unknown_fields`, `missing_required_fields`, `suggested_mappings` or
`decision: needs_correction`, correct the payload and rerun the plan before
calling apply. PLwC does not complete onboarding from a partial normalized
payload.
