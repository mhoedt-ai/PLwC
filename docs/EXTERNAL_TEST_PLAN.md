# PLwC Open Beta External Test Plan

Use this structured plan for an open beta smoke. Each step has an acceptance
criterion. If the actual result differs, report it with
[`BUG_REPORT_TEMPLATE.md`](BUG_REPORT_TEMPLATE.md).

Roles and prerequisites are described in
[`EXTERNAL_TESTER_GUIDE.md`](EXTERNAL_TESTER_GUIDE.md).

Use a disposable workspace and disposable files. Do not use real private data.

## A. Installation and Visibility

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 1 | Obtain the announced open beta MCPB package. | Package filename is `plwc-gateway-<version>.mcpb`. |
| 2 | Verify the package SHA256 against the announced value. | Hash matches exactly. |
| 3 | Enable Claude Desktop Developer Mode. | Extension Developer controls are available. |
| 4 | Install the MCPB in Claude Desktop. | Installation completes without an unexpected error. |
| 5 | Create or open a Claude Project for PLwC and add the supplied Project Instruction. | Project is ready for a new session. |
| 6 | Start a new session. | Session starts. |
| 7 | Inspect server visibility. | Exactly one PLwC server, `plwc-gateway`, is visible. |
| 8 | Inspect the public tool list. | Exactly eight public tools are visible: `plwc_status`, `plwc_describe`, `plwc_profile`, `plwc_reflection`, `plwc_governor`, `plwc_sandbox_run`, `plwc_workspace_operation`, `plwc_document_operation`. |
| 9 | Check for legacy public tool names. | Old tool names such as `plwc_compile_profile`, `plwc_write_workspace_file` and `plwc_governor_plan` are not visible. |

## B. Status and Setup

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 10 | Call `plwc_status(scope="first_run")`. | `greeting_message` is present; Docker status is clear (`running`, `daemon_not_running` or `missing`). |
| 11 | If the PLwC Project Instruction is reported as missing, add it and call `plwc_status(scope="first_run")` again. | `claude_user_system_prompt` is no longer listed in `missing_requirements`. |
| 12 | Call `plwc_status(scope="runtime")`. | Runtime reports `plwc-gateway`, expected version and public tool count 8. |
| 13 | Call `plwc_describe(scope="tools")`. | Tool list and operation guidance match the visible eight-tool facade. |
| 14 | Call `plwc_describe(scope="workspace_operation")`. | Workspace scope, protected boundaries and denial behavior are documented. |

## C. Workspace Operations

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 15 | Create or write a small disposable file through `plwc_workspace_operation(operation="write")`. | `policy_decision` is `ALLOW`; changed-file metadata is returned. |
| 16 | Read the disposable file through `plwc_workspace_operation(operation="read")`. | Content matches the write. |
| 17 | Search for a known token in the disposable workspace. | Results stay inside the configured workspace root. |
| 18 | Attempt parent traversal such as `path="../outside.txt"`. | `DENY` or validation failure; no mutation. |
| 19 | Attempt to write a protected profile/governance file such as `PERSONA.md`. | `DENY` with a protected-boundary reason; no mutation. |
| 20 | Run `exact_replace` without the expected count or with a missing token. | Fail-closed response; no unexpected mutation. |

## D. Document Operations

Before document creation, call `plwc_describe(scope="document_operation")`.
The accepted schema is documented there. Image paths must be workspace-relative;
external URLs are not accepted.

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 21 | Create a small PDF, DOCX, XLSX or PPTX through `plwc_document_operation`. | File is created inside the workspace and metadata is returned. |
| 22 | Inspect or extract text from the created artifact where supported. | Metadata or extracted text is plausible and bounded. |
| 23 | Try an external URL as an image path in a V2 image element. | `DENY`; only workspace-relative paths are accepted. |

## E. Sandbox and Safe Mode

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 24 | Call `plwc_status(scope="sandbox")`. | Docker and sandbox readiness are reported clearly. |
| 25 | If Docker is running, call `plwc_sandbox_run(lang="python", code="print(1+1)")`. | Output contains `2`; mode is Docker-backed. |
| 26 | If practical, stop Docker Desktop and repeat the sandbox status/run check. | Safe Mode is reported; no host-shell fallback occurs. If Docker cannot be stopped safely, mark this step `N/A`. |

## F. Reflection and Governance

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 27 | Write a meaningful reflection with evidence through `plwc_reflection`. | Accepted or rejected with clear semantic guidance; any accepted write is governed. |
| 28 | Submit a low-value technical log such as `pytest should pass` as a reflection. | Rejected with no reusable-insight style guidance. |
| 29 | Call `plwc_governor(operation="plan")` for a disposable memory-promotion candidate. | Plan is read-only and requires confirmation before any write. |
| 30 | Do not call `plwc_governor(operation="apply", confirmed=true)` unless the tester and maintainer explicitly approve a disposable mutation. | No unapproved durable profile or memory mutation. |

## G. Trust Boundary and Wrap-Up

| # | Step | Acceptance criterion |
| --- | --- | --- |
| 31 | Record whether the host exposes non-PLwC shell/filesystem tools. | Any bypass tools are documented as outside PLwC protection. |
| 32 | Record package version, SHA256, OS, Claude Desktop version and Docker status. | Report includes enough context to reproduce. |
| 33 | File one report per deviation. | Each report includes step number, expected behavior, actual behavior and relevant tool metadata. |

## Verdict Guidance

- `PASS`: all required steps pass or unsupported environment steps are marked
  `N/A` with a clear reason.
- `PASS_WITH_NOTES`: core PLwC behavior passes, but setup, Docker availability
  or host UI behavior needs follow-up.
- `FAIL`: the public boundary is wrong, governed denial behavior fails,
  unapproved mutation occurs, or the host cannot execute real PLwC tool calls.
