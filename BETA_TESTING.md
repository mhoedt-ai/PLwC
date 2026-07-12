# PLwC Open Beta Testing

This is the entry point for open beta testers.

PLwC is in **open beta** for privacy-filtered MCPB package testing. It is not a
final public release, not production-certified and not signed. Install only the
package/version that is explicitly announced for the current beta, and verify
the SHA256 before installing.

Current open beta baseline:

```text
Package: build/mcpb/plwc-gateway-0.2.0-rc18.dev9.mcpb
Version: 0.2.0-rc18.dev9
SHA256: 2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345
Status: package smoke PASS, Claude Desktop smoke PASS, Odysseus MCP smoke PASS
Signature: unsigned
```

Open beta means public testing of the privacy-filtered package and public-safe
documentation. It does **not** mean the private development repository can be
published as-is. Historical smoke reports and local evidence still need a
public-branch sanitization decision before source publication.

## What PLwC Is

PLwC is a governed MCP Gateway for Claude Desktop and other MCP clients. It
exposes one visible server, `plwc-gateway`, with exactly eight public facade
tools. File, document, sandbox, profile, reflection and memory-governance
operations run through policy checks and local audit metadata.

## What To Test

Follow the structured plan:

[`docs/EXTERNAL_TEST_PLAN.md`](docs/EXTERNAL_TEST_PLAN.md)

In short:

- Installation and visibility: exactly one server, exactly eight tools.
- Runtime and first-run status.
- Workspace list/read/write/search, including protected-path and traversal
  denial cases.
- Small document/PDF creation or inspection.
- Safe Mode and Docker sandbox behavior.
- Governed reflection and a read-only governor plan.

Tester roles and prerequisites:

[`docs/EXTERNAL_TESTER_GUIDE.md`](docs/EXTERNAL_TESTER_GUIDE.md)

## What Not To Test

- Do not expect enterprise or production certification.
- Do not use real personal files, real private profiles or real memory content.
- Do not use old public tool names from early scaffolds. PLwC v0.2 exposes the
  eight facade tools documented in the README.
- Do not treat the unsigned MCPB as trusted without SHA256 verification.
- Do not try to bypass PLwC through raw shell or filesystem tools when reporting
  PLwC behavior. If a host has bypass tools, document that trust boundary
  separately.
- Do not send private data in public bug reports.

## Known Limitations

The open beta baseline is intentionally limited. It has no OCR, no PDF
redaction, no digital signing, no form filling, no PDF/A claim, no
LibreOffice/Pandoc conversion, no macro execution, no runtime network access
and no HTML/CSS rendering pipeline.

The MCPB itself is unsigned. Integrity is currently established by exact SHA256
verification plus the recorded package/Desktop/Odysseus smoke evidence.

## Feedback

Use one issue per finding:

| Category | Use when |
| --- | --- |
| Bug | A tool fails, returns the wrong result or behaves differently from docs. |
| UX confusion | The wording, setup flow or response shape is unclear. |
| Security concern | A documented boundary appears not to hold. |
| Feature request | The idea is useful but not part of the current open beta scope. |

If issue templates are unavailable, use:

[`docs/BUG_REPORT_TEMPLATE.md`](docs/BUG_REPORT_TEMPLATE.md)
