# PLwC Dev 9 Open Beta Claude Desktop Quickstart

This is a literal step-by-step installation guide. It is written for a
normal Claude Desktop user, not for developers. Follow the steps in
order. If a step does not behave as described under "Expected result",
read the "If you do not see this..." line right under it.

> PLwC v0.2.0-rc18.dev9 is an **Open Beta**, not a final release. The
> MCPB is **not signed**. Verify the documented SHA256 and do not expect
> production certification or final-release guarantees.

> This quickstart is Claude Desktop-specific. For the maintainer-confirmed
> local GPT stdio route, the Odysseus stdio route and the hosted ChatGPT
> web/custom-app status, see [`INSTALLATION.md`](INSTALLATION.md).

---

## 1. What this guide is for

This guide installs PLwC as an **MCPB extension** in Claude Desktop.

There are two installation paths:

- **Normal user (MCPB installation)** — recommended.
  You install the prepared `plwc-gateway-0.2.0-rc18.dev9.mcpb` file inside
  Claude Desktop. You need Python 3.11 or newer, but you do **not** need Git.
- **Developer (source installation)** — only for contributors.
  You check out the repository, build the worker image yourself and
  build the MCPB yourself. See [`INSTALLATION.md`](INSTALLATION.md)
  for the developer path.

This quickstart covers the **normal user (MCPB)** path.

---

## 2. Official downloads

Use the official sources below. Do not download from third-party
mirrors.

- **Claude Desktop** (the app you install PLwC into):
  https://claude.ai/download

- **Claude Desktop Extensions / MCPB documentation**
  (how MCPB installation works in Claude Desktop):
  https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop

- **Docker Desktop for Windows** (required for the sandbox and the
  document worker that handles DOCX/XLSX/PPTX/PDF creation):
  https://docs.docker.com/desktop/setup/install/windows-install/

- **Python for Windows** — required by the packaged local `server.py` runtime
  and by source installations:
  https://www.python.org/downloads/windows/

- **Claude Code** — optional developer tooling, not required for
  normal use:
  https://code.claude.com/docs/en/setup

### What a normal MCPB user needs

- Claude Desktop installed.
- Claude Desktop **Developer Mode** enabled (see Section 4).
- The PLwC `.mcpb` file (currently `plwc-gateway-0.2.0-rc18.dev9.mcpb`).
- Python 3.11 or newer available on `PATH`.
- Docker Desktop installed and running, for sandbox / document worker
  features.

### What a developer additionally needs

- Git.
- Docker Desktop.
- Optionally Claude Code.
- A local source checkout of the PLwC repository.

---

## 3. Prerequisites

Before you start, confirm:

- Claude Desktop is installed on your computer.
- You can open Claude Desktop and reach Settings.
- The PLwC MCPB artifact `plwc-gateway-0.2.0-rc18.dev9.mcpb` is on disk
  somewhere you can find it (Downloads, a release folder, etc.).
- Python 3.11 or newer is installed and `python --version` works in a new
  terminal.
- Docker Desktop is installed. If Docker Desktop asks for the
  **WSL 2 backend** during installation, accept it.
- You have admin rights on the machine if Docker Desktop or
  Claude Desktop ask for an admin prompt.

Optional, only for developers:

- Git available on PATH.
- (Optionally) Claude Code installed.

---

## 4. Enable Claude Desktop Developer Mode

Local MCPB extensions can only be installed if Claude Desktop is in
Developer Mode.

1. Open Claude Desktop.
2. Open **Settings**.
3. Open the **Extensions** section.
4. Open **Advanced settings**.
5. Find **Extension Developer** / **Developer Mode**.
6. Enable Developer Mode.
7. If Claude Desktop asks you to restart, restart Claude Desktop.

**Expected result:** A local extension / MCPB install entry such as
**Install Extension** is now visible inside the Extensions area.

**If you do not see "Install Extension" or any local MCPB
installation option:**
Developer Mode is probably not enabled. Re-open Settings →
Extensions → Advanced settings → Extension Developer, enable
Developer Mode, and restart Claude Desktop.

---

## 5. Install the PLwC MCPB

1. Open Claude Desktop.
2. Open **Settings**.
3. Open **Extensions**.
4. Open **Advanced settings**.
5. Find **Extension Developer**.
6. Click **Install Extension**.
7. In the file picker, select the PLwC MCPB file. The current
   Open Beta artifact is:
   ```
   plwc-gateway-0.2.0-rc18.dev9.mcpb
   ```
   The expected SHA256 for download verification is:
   ```
   2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345
   ```
8. Confirm the installation in any Claude Desktop dialog that appears.
9. If Claude Desktop asks you to restart, restart it.

**Expected result:** PLwC now appears as the MCP server
`plwc-gateway` in Claude Desktop.

**If `plwc-gateway` does not appear:**
- Re-check Developer Mode (Section 4).
- Re-pick the correct `.mcpb` file in step 7.
- Restart Claude Desktop.

---

## 6. Create a Claude Project for PLwC

A Claude Project keeps PLwC behavior consistent across new
conversations. The project name does not technically matter, but the
**Project Instruction** does.

Recommended project name: `PLwC`.

1. Open Claude.
2. Open **Projects**.
3. Create a **new project**.
4. Name it:
   ```
   PLwC
   ```
5. Open the project settings / **project instructions**.
6. Paste the Project Instruction text from Section 7 (next).
7. Save the project instruction.
8. Start new PLwC work **inside this project**, not in unstructured
   conversations.

**Expected result:** Every new conversation in this Claude Project
starts by checking PLwC tools and compiling the active PLwC profile
before answering.

**If new conversations answer immediately and skip PLwC:**
The Project Instruction is probably missing or unsaved. Open the
project, paste the instruction, and save again.

---

## 7. Recommended Claude Project Instruction

Paste this text **as-is** into the project instructions. It uses v0.2
public tool names. Do not edit it to use old v0.1 tool names — the
instruction explicitly blocks them.

```
Before you answer any user message, run tool_search("plwc") and compile the active PLwC profile in boot mode.

Do not answer the first user message until the active PLwC profile has been successfully compiled.

At the beginning of every new session:
1. Run tool_search("plwc").
2. If PLwC tools are not visible, report that PLwC is not available in this session.
3. If PLwC tools are visible, call plwc_profile with operation="compile" and compile_mode="boot".
4. Treat the returned compiled_layer as binding working context for this session.
5. Use compile_mode="working" with task_context for a larger task-specific layer, and compile_mode="full" only for audit or diagnosis.

Use the compiled_layer as the authoritative session context for:
- role
- name
- tone
- working style
- initiative limits
- memory rules
- confirmation boundaries
- governance requirements

You remain Claude, but you must work consistently within the active PLwC profile. Do not independently deviate from the active PLwC profile. Do not invent a profile if profile compilation fails.

If profile compilation reports setup_required or unavailable:
1. Call plwc_status with scope="first_run".
2. Call plwc_profile with operation="status".
3. Briefly explain what is missing and what the user needs to do next.

Profile, memory, reflection and governance files must not be edited directly through workspace access.

For profile, memory, reflection and governance changes, use only the governed PLwC flows:
- plwc_reflection for reflection writes
- plwc_governor with operation="plan" for governed plans
- plwc_governor with operation="apply" for confirmed governed applies

Critical changes require the intended PLwC governance flow and explicit confirmation where required.

A chat command does not end the active PLwC profile. To stop using PLwC, the user must disable PLwC in Claude Desktop.

Do not use old v0.1 public tool names. In v0.2, the public tools are:
- plwc_status
- plwc_describe
- plwc_profile
- plwc_reflection
- plwc_governor
- plwc_sandbox_run
- plwc_workspace_operation
- plwc_document_operation

The following old individual tool names are not public tools in v0.2 and must not be used:
- plwc_compile_profile
- plwc_first_run_status
- plwc_profile_status
- plwc_governor_plan
- plwc_governor_apply
- plwc_write_reflection
- plwc_write_workspace_file
- plwc_read_workspace_file
```

---

## 8. Verify that PLwC is installed correctly

Run these two checks inside a new conversation in your PLwC project.

### 8.1 Runtime check

Call:
```
plwc_status with scope="runtime"
```

**Expected result:**

- `server` is `plwc-gateway`.
- `registered_public_tool_count` is `8`.
- An `active_profile` value is reported (it may be `default` until you
  set a real profile).
- A workspace status is reported.

**If the call fails because no scope was provided:**
You called `plwc_status` without a scope. Add `scope="runtime"`.

### 8.2 Public-tool listing

Call:
```
plwc_describe with scope="tools"
```

**Expected result:** the public tools are exactly:

- `plwc_status`
- `plwc_describe`
- `plwc_profile`
- `plwc_reflection`
- `plwc_governor`
- `plwc_sandbox_run`
- `plwc_workspace_operation`
- `plwc_document_operation`

The following **old** v0.1 tool names must NOT appear as public tools:

- `plwc_write_workspace_file`
- `plwc_read_workspace_file`
- `plwc_governor_plan`
- `plwc_governor_apply`
- `plwc_compile_profile`
- `plwc_write_reflection`

**If old tool names do appear:**
You have a stale or wrong PLwC installation. Re-install the current
MCPB file from Section 5.

---

## 9. Docker Desktop setup

PLwC's sandbox and document worker run inside Docker. You only need
this section if you also want sandbox/document operations
(DOCX/XLSX/PPTX/PDF creation, ZIP, PDF processing, sandboxed code).

1. Open https://docs.docker.com/desktop/setup/install/windows-install/
2. Download Docker Desktop for Windows.
3. Run the installer.
4. If asked, use the **WSL 2 backend**.
5. If Docker asks for a Windows restart, restart Windows.
6. Start Docker Desktop after the restart.
7. Wait until Docker Desktop shows it is running (the whale icon is
   stable and the dashboard reports "Engine running").

**Expected result:**
```
plwc_status with scope="sandbox"
```
reports Docker / sandbox as ready, or reports a clear missing /
disabled state.

**Important:** PLwC does **not** silently fall back to running shell
commands on the host. If Docker is missing or stopped, sandbox and
document-worker functions are unavailable or limited, but the state is
always reported clearly. There is no hidden host execution path.

**If Docker stays in "Starting..." for a long time:**
Restart Docker Desktop, restart Windows once if Docker recently
updated, and confirm WSL 2 is healthy
(`wsl --status` in a PowerShell window for advanced checks).

---

## 10. Workspace setup

The workspace is the folder on your computer where PLwC creates and
reads normal project files (documents, smoke artifacts, drafts).

Recommended workspace path (example):
```
C:\Users\<YOU>\Claude_Arbeitsumgebung
```

Use any folder that:

- belongs to you,
- is **not** inside the PLwC source tree,
- is **not** a profile or governance folder,
- you are willing to share with Claude through PLwC.

Profile, memory, reflection and governance files are **protected** and
must not be edited directly through workspace operations. PLwC blocks
that by design.

---

## 11. First workspace smoke test

This is a tiny check that PLwC's workspace operations work. It is
**not** the full release smoke. Run it inside a PLwC project
conversation.

### Step 1 — create a test folder

Call:
```
plwc_workspace_operation with operation="create_dir" and path="plwc_test"
```
**Expected result:** the folder `plwc_test` is created inside your
workspace.

### Step 2 — write a file

Call:
```
plwc_workspace_operation with operation="write" and path="plwc_test/hello.txt"
```
(set `content` to a short string like `"Hello PLwC"`.)

**Expected result:** the file `plwc_test/hello.txt` is written.

### Step 3 — read the file back

Call:
```
plwc_workspace_operation with operation="read" and path="plwc_test/hello.txt"
```
**Expected result:** the file content is returned.

### Step 4 — try to write a protected file

Try:
```
plwc_workspace_operation with operation="write" and path="PERSONA.md"
```
**Expected result:** **DENIED**. This is correct. Profile and
governance files cannot be edited directly through workspace
operations.

---

## 12. First document smoke test

This is a tiny check that document creation works. Keep it small. Run
inside the PLwC project.

### Option A — small PDF

Call:
```
plwc_document_operation with operation="create_pdf" and output_path="plwc_test/hello.pdf"
```
and pass a small inline content payload, for example:
```
{ "title": "Hello PLwC", "lines": ["First line.", "Second line."] }
```

**Expected result:**
- the file `plwc_test/hello.pdf` is created in the workspace,
- `plwc_document_operation` with `operation="inspect_pdf"` reports a
  valid PDF,
- `plwc_document_operation` with `operation="extract_pdf_text"` returns
  the document text.

### Option B — small DOCX

Call:
```
plwc_document_operation with operation="create_docx" and output_path="plwc_test/hello.docx"
```
with a tiny `{ "title": "Hello PLwC", "paragraphs": ["First.", "Second."] }`.

**Expected result:** the DOCX is created, `inspect_docx` succeeds, and
`extract_docx_text` returns the text.

If both succeed, document creation is working end-to-end. The full
DOCX V2 / XLSX V2 / PPTX V2 / PDF V2 release smoke is much larger and
lives in the release-smoke evidence, not in this quickstart.

---

## 13. Troubleshooting

### `plwc_status` without a scope fails

Use an explicit scope:
- `runtime`
- `sandbox`
- `first_run`
- `config`

Example: `plwc_status with scope="runtime"`.

### `write_file` or `plwc_write_workspace_file` does not exist

These are **old v0.1 names** that are no longer public. Use:
```
plwc_workspace_operation with operation="write"
```

### The target folder does not exist

Create it first:
```
plwc_workspace_operation with operation="create_dir"
```

### `exact_replace` fails

Pass `expected_replacements` as an integer:
```
plwc_workspace_operation with operation="exact_replace",
  path="...", old_text="...", new_text="...", expected_replacements=1
```

### Only 5 (or some other small number) of PLwC tools appear in `tool_search`

`tool_search` may show only a subset per query depending on Claude
Desktop's context. The authoritative source of truth is:

- `plwc_status with scope="runtime"`, and
- `plwc_describe with scope="tools"`.

Both should report exactly **8** public PLwC tools.

### Docker unavailable

Start Docker Desktop and wait until the dashboard reports
"Engine running". Then re-run `plwc_status with scope="sandbox"`.

### `Install Extension` is not visible

Enable Claude Desktop **Developer Mode** (Section 4) and restart
Claude Desktop.

### Claude answers before loading the PLwC profile

The Project Instruction is missing or unsaved. Open the project's
instruction, paste the text from Section 7, save, and start a new
conversation in the project. The first session action must be
`tool_search("plwc")` followed by
`plwc_profile(operation="compile", compile_mode="boot")`.

### Claude tries to call `plwc_compile_profile`

That is an **old v0.1 tool name**. In v0.2 use:
```
plwc_profile(operation="compile", compile_mode="boot")
```

Use `compile_mode="boot"` for normal session startup. Use
`compile_mode="working"` with `task_context` for a bounded task layer. Use
`compile_mode="full"` only for audit or diagnosis.

### Claude tries to call `plwc_governor_plan` or `plwc_governor_apply`

Those are **old v0.1 tool names**. In v0.2 use:
```
plwc_governor(operation="plan")
plwc_governor(operation="apply")
```

### Claude tries to call `plwc_write_reflection`

That is an **old v0.1 tool name**. In v0.2 use:
```
plwc_reflection(operation="write", ...)
```

### Stale `STATE.json` / mismatched active profile warning

PLwC reports a setup warning if its on-disk active-state file points at
a profile that does not match the configured active profile. The
configured profile wins. Treat this as a **setup warning**, not a
failure, unless behavior is actually wrong.

---

## 14. Full release smoke tests

This quickstart only verifies that PLwC is installed and reachable.

The full v0.2 release smoke is much larger and covers Office V2,
PDF V2, ZIP, read_image, PBA2/Governor, protected boundary, sandbox
and existing PDF MVP operations.

For the public Open Beta test scope, current package hash and reporting rules,
see [`BETA_TESTING.md`](../BETA_TESTING.md).

Internal release evidence and private smoke transcripts are intentionally not
included in the public snapshot.

Once those checks pass on a clean install, PLwC remains within its
v0.2.0-rc18.dev9 Open Beta scope. A final release is not yet cut.
