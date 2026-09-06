# PLwC 1.0 Pre-release Distribution Workflow

Maintainer document.

This workflow describes how PLwC privacy-filtered MCPB and Windows Setup
pre-release artifacts are published while preserving the security and privacy
boundaries of the development tree. It does not create a production-certified
release or authorize browser Store publication.

## 1. Pre-release Rules

- Open beta distribution is package-first: publish or share the
  privacy-filtered MCPB plus public-safe notes.
- Do not publish the private development repository as-is. Historical smoke
  reports, local paths and private evidence require a separate public-branch
  sanitization decision.
- The package remains a pre-release/beta artifact, not `latest`, not stable and
  not production-certified.
- The MCPB is unsigned. The exact SHA256 is mandatory for every open beta
  package.
- Public boundary must remain one visible MCP server, `plwc-gateway`, with
  exactly eight public facade tools.
- No source A/B MCP server, raw Commander endpoint, raw PBA endpoint, direct
  host shell or second PLwC MCP server may be exposed.

## 2. Current 1.0 pre-release baseline

```text
Version: 1.0.0
Gateway package: build/mcpb/plwc-gateway-1.0.0.mcpb
Gateway package SHA256: 5e870f40b9b3faea79d3997af9c657ef62c11295e85635a049214f7b63678fe7
Windows Setup: PLwC-Setup-1.0.0-installer-r24.exe
Windows Setup SHA256: b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0
Windows Setup release: https://github.com/mhoedt-ai/PLwC/releases/tag/plwc-setup-1.0.0-installer-r24
Signature: explicit unsigned / Authenticode NotSigned
Installer contracts: 69 PASS
Configuration integration tests: 13 PASS
Browser extension tests: 173 PASS
Store package identity and secret scan: PASS
Store-signed live-browser acceptance: PENDING
```

Historical rc18 and rc19 artifacts remain historical evidence. Their filenames,
hashes and conclusions must not be edited or reused as 1.0 identities.

## 3. Prepare an artifact

1. Start from a clean working tree or record any intentional uncommitted
   release-evidence changes.
2. Run the focused source validation for the slice under test.
3. Build the MCPB from a staging tree.
4. Apply the PR-005 public payload filter before packing.
5. Inspect the package payload for:
   - private smoke reports;
   - release-position/private evidence docs;
   - local profiles outside `profiles/template/`;
   - workspace data;
   - logs;
   - build/dist artifacts;
   - tests/caches;
   - `.env`;
   - real `config/security.yaml`;
   - nested MCPB files.
6. Record SHA-256, size and file count.
7. Run extracted-package smoke.
8. Run host smoke where applicable, at minimum Claude Desktop for the Desktop
   package and Odysseus when claiming Odysseus MCP support.
9. For Windows Setup, bind the installer revision, external identity, payload
   manifest, exact EXE hash, signature disposition and acceptance record.
10. Never run a validation path that overwrites the accepted `stage` or `dist`
    evidence tree; test builds use isolated output roots.

## 4. Publish or Share the Pre-release Artifact

Open beta may use a public GitHub pre-release, a public download location or a
maintainer-announced package channel. Use only public-safe notes.

Release notes must include:

- package or Setup filename;
- version;
- SHA256;
- size;
- signature status (`unsigned`);
- installer revision when applicable;
- exact public tool count and server name;
- smoke reports used for the beta decision;
- known limitations;
- no final-release or production claim;
- security and privacy warnings for testers.

If using GitHub Releases:

1. Create an immutable tag for the beta commit or package evidence commit.
2. Create a release marked as **pre-release**.
3. Do not mark it as latest.
4. Upload the MCPB asset.
5. Include SHA256 and a warning that the package is unsigned.
6. Do not attach private evidence files or local transcripts.

## 5. Tester Communication Checklist

```text
[ ] Exact package or Setup filename provided
[ ] Version provided
[ ] SHA256 provided
[ ] Signature status clearly says unsigned
[ ] Installer revision and acceptance record linked when applicable
[ ] Link to BETA_TESTING.md
[ ] Link to docs/EXTERNAL_TESTER_GUIDE.md
[ ] Link to docs/EXTERNAL_TEST_PLAN.md
[ ] Link to docs/BUG_REPORT_TEMPLATE.md
[ ] Warning: do not use real private files/profiles/memory
[ ] Warning: not final/stable/production-certified
[ ] Known limitations linked or summarized
```

## 6. Feedback Handling

- One report per issue.
- Bugs and UX confusion go into the next development slice.
- Security concerns get priority triage.
- Feature requests go to the backlog unless Mirco explicitly scopes a new
  requirement.
- Do not change the public tool surface in response to beta feedback without an
  explicit requirement, traceability update and tests.

## 7. What Never Happens

- No force-push or tag move for a published beta artifact.
- No silent replacement of an uploaded MCPB.
- No silent replacement of an uploaded Setup EXE or its external build identity.
- No final-release claim while the package is unsigned and the release checklist
  remains in manual review.
- No browser Store submission or publication merely because a GitHub
  pre-release exists.
- No publication of the private development repository without public-branch
  sanitization.
- No bundled private evidence, local runtime data, real profiles or real
  workspaces in the MCPB.
