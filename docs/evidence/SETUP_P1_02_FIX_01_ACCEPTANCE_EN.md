# Windows Setup P1-02 Fix 01 Acceptance Evidence

Date: 2026-08-08

Scope: `SETUP-P1-02-FIX-01` only. This correction expands the post-install
Getting Started experience and advances Windows Setup to `installer-r16`.
Gateway `0.2.0-rc18.dev10` and Chat Bridge `0.2.0-rc19.dev20` remain unchanged.

## Purpose

VM review of the r15 guide confirmed that the operational workflows were
present, but the opening path focused too strongly on Chat Bridge and the core
terms were too terse for a normal user. The corrected guide must explain every
supported installation path and describe what each recurring PLwC workflow is
for, when it is useful, and what it can change.

## Implemented Contract

The local English and German guides begin with five component-aware paths:

- PLwC Gateway only;
- Claude Desktop MCPB import;
- Codex STDIO TOML activation;
- Odysseus STDIO JSON activation;
- Chat Bridge unpacked-extension activation.

Only the Chat Bridge path uses the versioned Primer. Native MCP clients receive
the eight live tool schemas directly. Every client supports normal-language
requests, while uncertain operations must be discovered through
`plwc_describe` instead of being guessed.

The guide explains Status, Describe, onboarding, Compile, Reflection, Governor,
diary, Trashcan, Persona promotion, and Force in plain language. Each section
states the purpose, when to use it, and whether it changes data. Compile is
explicitly defined as a read-only load of the active profile into a governed
context layer, not compilation of program code.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Five installation paths | PASS | Contract tests require the component marker, exact generated client files, and Gateway-only guidance. |
| Primer limited to Chat Bridge | PASS | Both guides distinguish native MCP schema delivery from the Bridge-only Primer. |
| Normal-language operation | PASS | Both guides require natural-language use and `plwc_describe` discovery. |
| Plain-language workflow purpose | PASS | Tests require plain-language, use-time, change-effect, and read-only wording. |
| Compile meaning | PASS | Tests require active profile, context layer, no program-code compilation, and read-only behavior. |
| Local and self-contained | PASS | Contract tests reject remote URLs, scripts, and remote stylesheet assets. |
| Bind Setup r16 identity | PASS | Installer source, artifact, payload manifest, external identity, and evidence package agree on r16/FIX-01. |

## Verification

Automated verification completed on 2026-08-08:

- Gateway: `45 passed`, `6 skipped`.
- Node Bridge: `23 passed`, `0 failed`.
- Browser Extension: `140 passed`, `0 failed`.
- Focused Getting Started and clean-machine UI contracts: `45 passed`,
  `0 failed`.
- Full Windows installer Pester suite: `64 passed`, `0 failed`.
- Guarded production UI smoke, English: passed all 10 wizard pages and stopped
  on `Install` before installation.
- Guarded production UI smoke, German: passed all 10 wizard pages and stopped
  on `Installieren` before installation.

Production artifact:

```text
installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r16.exe
Size: 5,192,490 bytes
SHA-256: 7a3d5d0c320cc2cd05f2f850088a26be654b57438fb3cf8ecd7134e99b1b2c05
```

The external build identity records the same executable hash and binds:

```text
Gateway:           0.2.0-rc18.dev10
Node Bridge:       0.2.0-rc19.dev20
Browser Extension: 0.2.0-rc19.dev20
Native Launcher:   0.2.0-rc19.dev20
Evidence package:  SETUP-P1-02-FIX-01
```

Payload manifest:

```text
Artifact: PLwC-0.2.0-rc18.dev10-payload-manifest.json
SHA-256: 9b6e372205af455b1d77564f9241183830fc7ab6464a9a24e3dc84713a307f0e
Payload size: 17,549,467 bytes
```

Packaged guide records:

```text
common/docs/getting-started-en.html
  26,202 bytes
  3ecda661f0103bed9a54a8cb22fa4e2ce8e8a1ad93cddbae5331ae18383ffbc5
common/docs/getting-started-de.html
  28,477 bytes
  5d89327d1ef971d539b31455f07ca25286292ce434cc5df949f7e590a347c60e
common/docs/getting-started.css
  5,473 bytes
  4ff2c765f0c0bba75c2019f6e9a15e45e7590b735f8068dd625a6f69d9ac1d1f
```

## Remaining Gate

The exact r16 executable requires a preserved-VM review confirming that the
selected-language guide renders correctly and that the component path and
plain-language workflow descriptions are understandable to a normal user.
