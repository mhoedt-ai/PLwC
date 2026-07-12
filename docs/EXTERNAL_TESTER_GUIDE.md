# PLwC Open Beta Tester Guide

This guide is for open beta testers of the privacy-filtered PLwC MCPB package.
The package is available for public testing, but it is still a beta artifact:
it is unsigned, not production-certified and not a final public release.

Use the structured acceptance plan in
[`EXTERNAL_TEST_PLAN.md`](EXTERNAL_TEST_PLAN.md). Report issues with
[`BUG_REPORT_TEMPLATE.md`](BUG_REPORT_TEMPLATE.md) when issue templates are not
available.

## 1. What PLwC Is

PLwC is a governed MCP Gateway for Claude Desktop and other MCP clients. It
exposes exactly one visible MCP server, `plwc-gateway`, with exactly eight
public facade tools. File, document, sandbox, profile, reflection and
memory-governance operations pass through policy checks and local audit
metadata.

Open beta testing is meant to verify installability, tool discovery, governed
ALLOW/DENY behavior, documentation clarity and host integration behavior. It is
not a production certification.

## 2. Tester Roles

Pick one role for a test pass.

### Role A: Normal User

- Checks whether installation and quickstart wording are understandable.
- Focuses on what is confusing, surprising or under-explained.
- Does not need to read source code.

### Role B: Technical User

- Checks Docker availability, Claude Desktop Developer Mode, MCPB
  installation, SHA256 verification, tool visibility, logs and sandbox status.
- May inspect logs, but should not patch the source during a beta smoke.

### Role C: Security-Aware Tester

- Checks documented boundaries against observed behavior.
- Focuses on workspace scope, protected profile/governance paths, traversal
  denial, the eight-tool public boundary, sandbox behavior and
  reflection/governor controls.
- Reports credible boundary failures as security concerns.

## 3. Prerequisites

- Claude Desktop with Developer Mode enabled.
- Docker Desktop installed and running for sandbox and document-worker testing.
  Without Docker, PLwC should report Safe Mode: workspace/profile operations can
  still work, but sandboxed code execution is disabled.
- The announced open beta MCPB package.
- The expected SHA256 for that exact package.
- A disposable workspace and, if profile/governance behavior is tested, a
  disposable profile.

Current baseline:

```text
Package: plwc-gateway-0.2.0-rc18.dev9.mcpb
SHA256: 2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345
Signature: unsigned
```

## 4. Test Flow

1. Download the announced MCPB package from the open beta distribution channel.
2. Verify the SHA256 exactly before installing.
3. Install the MCPB in Claude Desktop.
4. Create or open a Claude Project for PLwC and add the PLwC Project
   Instruction if supplied with the beta package.
5. Start a new session and verify `plwc-gateway` is visible.
6. Work through [`EXTERNAL_TEST_PLAN.md`](EXTERNAL_TEST_PLAN.md).
7. Report one issue per problem, including the test step, expected behavior,
   actual behavior and relevant metadata.

## 5. What Testers Should Not Do

- Do not use real personal files, real private profiles or real memory content.
- Do not share private profile files, audit logs or memory data in public
  issues.
- Do not install a package whose SHA256 does not match the announced value.
- Do not use old public tool names from early scaffolds. Use the eight facade
  tools only.
- Do not provide external URLs to document/image operations; workspace-relative
  paths are required.
- Do not use host shell or host filesystem bypass tools as evidence for PLwC
  behavior. If the host exposes bypass tools, record that separately as a trust
  boundary note.
- Do not treat open beta as stable, signed or production-ready.

## 6. Results

The most useful feedback is precise and small:

- which step you ran;
- the tool call or UI action;
- expected result;
- actual result;
- whether Docker was running;
- the package version and SHA256;
- any relevant policy decision, error category or audit metadata.
