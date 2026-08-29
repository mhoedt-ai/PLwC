# PLwC 1.0 Pre-release Testing

This is the entry point for open beta testers.

PLwC 1.0 is available as an explicit unsigned pre-release candidate for
privacy-filtered package and Windows Setup testing. It is not
production-certified. Install only the exact announced artifact and verify its
SHA-256 before running it.

Current pre-release baseline:

```text
Gateway package: build/mcpb/plwc-gateway-1.0.0.mcpb
Gateway package SHA256: 5e870f40b9b3faea79d3997af9c657ef62c11295e85635a049214f7b63678fe7
Windows Setup: PLwC-Setup-1.0.0-installer-r24.exe
Windows Setup SHA256: b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0
Windows Setup URL: https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r24/PLwC-Setup-1.0.0-installer-r24.exe
Status: installer, installed update, Gateway, Bridge and extension gates PASS; Store-signed browser acceptance PENDING
Signature: explicit unsigned / Authenticode NotSigned
```

Pre-release means public testing of privacy-filtered artifacts and public-safe
documentation. It does **not** mean every historical or local artifact is a
release candidate. Never substitute an older installer or relabel historical
evidence as r24.

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
- Do not use old public tool names from early scaffolds. PLwC 1.0 exposes the
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

The MCPB and r24 Setup are unsigned. Integrity is currently established by
exact external SHA-256 verification plus the recorded package, installed
update, Bridge and client evidence. Chrome and Edge Store packages remain
controlled drafts and are not public downloads.

## Feedback

Use one issue per finding:

| Category | Use when |
| --- | --- |
| Bug | A tool fails, returns the wrong result or behaves differently from docs. |
| UX confusion | The wording, setup flow or response shape is unclear. |
| Security concern | A documented boundary appears not to hold. |
| Feature request | The idea is useful but not part of the current pre-release scope. |

If issue templates are unavailable, use:

[`docs/BUG_REPORT_TEMPLATE.md`](docs/BUG_REPORT_TEMPLATE.md)
