# PLwC Update Center

The r26 source line contains one local Update Center shared by the Windows
installation and configuration experience. It is implemented in the Gateway
package rather than the browser bridge, so PLwC installations without the Chat
Bridge can use the same verification rules.

## Release manifest

An accepted manifest must be UTF-8 JSON matching
`config/release-manifest.schema.json`. It contains:

- manifest schema, product version, and installer revision;
- component versions and compatibility ranges;
- publication time and recommended/required classification;
- German and English release notes;
- HTTPS artifact URL, exact byte size, and SHA-256;
- the artifact build identity bound to the same SHA-256;
- one RSA/SHA-256 signature over the canonical JSON representation.

PLwC rejects duplicate JSON members, unknown keys, unsafe artifact names,
non-HTTPS URLs, unknown signing keys, invalid signatures, mismatched hashes, and
unsupported build identities. It verifies the signature before trusting any
artifact metadata.

## Trust and caching

Trusted public release keys are read from `config/release-trust.json`. Private
keys never belong in the repository or installation. The r26 release candidate
pins the 4096-bit RSA public key
`plwc-release-r1-6bc3b440c598c407` (public-key SHA-256
`6bc3b440c598c407f1b685b136ad89cccb344f25c6b02d5d10fe72c3bfa8dcda`).
Its private key is stored separately from the repository and protected for the
release operator by Windows DPAPI.

Only a signature-verified manifest becomes `last-valid-manifest.json`. A failed
or offline check records its own time and error but cannot replace that valid
cache. Automatic checks are limited to one attempt per six hours; the manual
check remains available. No profile, workspace, prompt, or document content is
sent by the updater, and there is no telemetry.

## Download and installation

The Update Center uses three distinct states:

1. Review a plan containing the immutable plan ID, artifact name, size,
   SHA-256, and build identity.
2. Explicitly confirm the download. A partial, short, oversized, or wrong-hash
   file is rejected and no executable remains.
3. Separately confirm the interactive installer start. PLwC rechecks size,
   SHA-256, and signed build identity immediately before launch.

The updater does not run silently. The r26 installer owns migration, postflight,
failure reporting, and rollback. If it fails, the Update Center surfaces the
installer's `last-failure.json` path when present.

## Status meanings

- `update_available`: the live manifest was verified; inspect `update_kind`
  (`recommended` or `required`).
- `offline`: the check failed without a trusted live response; the last valid
  time and cached release remain visible.
- `rejected`: received content failed the manifest or signature contract.
- `never_checked`: no check has completed on this installation.

A missing or empty trust store is fail-closed, not an indication that an
unsigned manifest should be accepted.
