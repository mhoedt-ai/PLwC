# Smoke-Test Evidence

Status: 2026-07-17

This document summarizes the relevant smoke and governance evidence in anonymized form. It contains no links to raw reports or local source files. It only references the two other English files in this evidence folder:

- [TAGEBUCH_EN.md](TAGEBUCH_EN.md) - anonymized development narrative
- [CHANGE_HISTORY_EN.md](CHANGE_HISTORY_EN.md) - condensed change history

## Current Evidence Status

The smoke evidence reaches further back than the rc16-rc18 line. The Claude work folder contains older reports from 2026-05-23 through 2026-07-11. This file summarizes the full discoverable chain without linking to the original files or local paths.

The strongest current technical baseline is the rc18.dev9 line:

- Package smoke: PASS
- Desktop smoke: PASS
- public server: `plwc-gateway`
- public facade tools: exactly 8
- no public raw PBA, raw Commander, filesystem or second PLwC server
- package privacy filtering: PASS
- persona layer explicitly controllable
- CLU Doctor read-only
- reflection aliases verified
- cross-profile reflection write correctly blocked

Important: an earlier package report still said that Desktop smoke had not yet run for rc18.dev9. That statement was superseded by the later rc18.dev9 Desktop smoke.

## Eight Public Facade Tools

The current public boundary consists of exactly these eight tools:

| Tool | Role |
| --- | --- |
| `plwc_status` | Runtime, first-run and configuration status |
| `plwc_describe` | Tool, policy, Governor, reflection and workspace descriptions |
| `plwc_profile` | Compile, doctor, scan and profile operations |
| `plwc_reflection` | Governed reflection write path |
| `plwc_governor` | Plan/apply for profile, memory, persona and temperament |
| `plwc_sandbox_run` | Controlled sandbox execution |
| `plwc_workspace_operation` | Path-scoped workspace operations |
| `plwc_document_operation` | Controlled document operations |

The smoke tests repeatedly verify that no additional legacy or raw tools are publicly visible.

## Smoke Timeline

| Date | Line | Result | Core Finding |
| --- | --- | --- | --- |
| 2026-05-23 | v0.2.0-dev focus smoke | PASS | Reflection/Governor path in the real client: 8 tools visible, valid reflections accepted, technical garbage rejected, cross-profile guard active, plan/apply with `confirmed=true`, duplicate safety. |
| 2026-06-03 | rc2.dev0 consolidated | PASS | Public boundary, protected-path DENY, workspace write/read/copy/binary, ZIP extraction, memory-promotion admin override and force limits verified; 595 tests passed in that line. |
| 2026-06-04 | External test plan | PASS with findings | External usage plan confirms 8 tools, workspace protection, traversal DENY, PDF/document operations, sandbox and reflection/governance; findings concern docs/error wording, not hard gates. |
| 2026-06-05 | rc4 desktop | GREEN with finding | 8-tool boundary, workspace protection, document operations, sandbox, reflection/governance and new `edit_docx` with 5 edit types verified; only finding: external URL was functionally blocked but classified late/poorly. |
| 2026-06-09 | rc5 desktop | GREEN with findings | URL validation before worker confirmed, Node.js sandbox introduced, Node happy path and Node security DENYs passed; findings only micro/UX level. |
| 2026-06-10 | rc6 desktop | GREEN | 75 steps A-L passed: temperament promotion, INNER content gates, journal provenance, Node retest and governance DENYs; initial transport/test-criteria findings closed. |
| 2026-06-10 | rc7 desktop | GREEN | Journal provenance SHA fix, CRLF/LF roundtrip and session-end journal prompt confirmed; no open blockers. |
| 2026-06-13 | rc8 initial | FAIL due to test data | Memory-retire/temperament/reflection gates failed on abstract or invalid test inputs; semantic gate correctly blocked instead of blindly accepting. |
| 2026-06-13 | rc8 follow-up | PASS | With semantically valid inputs, memory promotion, retire, duplicate safety, compiled-layer exclusion of retired entries, compile tracking, no-action-rule, temperament promotion and journal provenance passed. |
| 2026-06-14/15 | rc9 main run + Qdrant follow-up | GREEN with findings | Main run confirms A-N mostly; Qdrant initially blocked by disabled flag; follow-up confirms reindex/retrieve/staleness/require_fresh/include_retired/drop_index/canonical integrity. |
| 2026-06-30 | rc12.dev1 compile modes | PASS with non-blocking gaps | Boot/working/full compile modes produce expected sizes and section selection; file immutability partly self-reported rather than independently hashed. |
| 2026-06-30 | rc12.dev2 desktop | PASS | Search scope guards reduce large live-root search from minutes to seconds; binary/too-large/excluded-dir skips visible; desktop stays responsive; compile modes non-regressing. |
| 2026-07-01 | rc13.dev0 desktop | GREEN | scan_tagebuch disconnect guard, inner-perspective reflection contract, Qdrant crash guard and compile independence confirmed; semantic retrieve still not load-bearing. |
| 2026-07-01 | rc14.dev0 desktop | PASS | Qdrant runtime guard, working semantic memory, boot fallback, drop-index fallback and content-aware superseded review verified; no fabricated duplicate check forced. |
| 2026-07-02 | rc15.dev0 Qdrant readiness | PARTIAL / package-only | Extracted-package smoke is recorded as passed; Desktop/MCP transport smoke had not yet run in that file. Later rc16 evidence addresses the observed transport-stall problem. |
| 2026-07-05 | rc16.dev0 | PASS | Qdrant reindex timeouts are handled structurally; no global gateway stall. |
| 2026-07-05 | rc17.dev0 | PASS | CLU Doctor, workspace diagnostics, journal guard and temperament threshold work after the fix build. |
| 2026-07-06 | rc18.dev0 package | PASS | Command catalog remains discovery-only; public boundary remains at eight tools. |
| 2026-07-07 | rc18.dev0 desktop | PASS | CLU Runner is read-only; no profile or workspace leaks; rc17 regressions hold. |
| 2026-07-08 | rc18.dev1 desktop | PASS with process note | Qdrant source-current consistency, reindex after confirmation, working compile with fresh semantic memory and protected boundary confirmed; restart required to activate new runtime. |
| 2026-07-08 | rc18.dev2 desktop | FAIL | Persona-layer settings toggle does not reach runtime; per-call override works, but extension-config wiring is broken. |
| 2026-07-08 | rc18.dev3 desktop | PASS | dev2 regression fixed: inverted `persona_layer_disabled` switch reaches runtime; compile can omit PERSONA; public boundary holds. |
| 2026-07-08 | rc18.dev4 desktop | FAIL | Persona-layer disablement removes PERSONA, but CORE role/working-context lines are not stripped cleanly yet; matching logic insufficient. |
| 2026-07-08 | rc18.dev6 desktop | PASS_WITH_NOTES | CORE leak closed, onboarding can be planned without persona-only required fields, Doctor read-only; icon still visually verifiable only. |
| 2026-07-09 | rc18.dev7 desktop | PASS_WITH_NOTES | Tool boundary, first-run bootstrap, active-profile precedence and persona-layer disablement confirmed. |
| 2026-07-10 | rc18.dev9 package | PASS | Privacy payload filtering, reflection aliases, onboarding metadata and public boundary confirmed. |
| 2026-07-11 | rc18.dev9 desktop | PASS | Install/runtime, SHA check, privacy sanity, first-run, precedence, Doctor and reflection alias checks passed. |
| 2026-07-17 | Browser/ChatGPT engine | PASS as working evidence | Workspace access works under control; desktop write outside allowed roots is blocked with DENY. |

## Historical Smoke Findings

The older smoke chain matters because it shows that later features did not appear suddenly. They build on repeated regressions and fixes.

### 2026-05-23 - Reflection/Governor Focus

Early evidence covered:

- exactly eight public tools;
- Reflection Validator accepts real insights;
- technical status statements are rejected from reflection;
- cross-profile write protection blocks writes to inactive profiles;
- Governor plan/apply with `confirmed=true` works;
- `confirmed=false` is blocked;
- repeated application of an already processed plan becomes duplicate/no-op.

### rc2.dev0 - Workspace and Governor P0

rc2.dev0 already covered several foundations:

- protected-path DENY for profile/persona files;
- workspace write/read;
- file-to-file copy instead of ambiguous write+source_path;
- byte-exact binary reads/writes;
- ZIP extraction with collision protection;
- memory_promotion with force override only for threshold denials;
- force does not override semantic, trust, duplicate, conflict or cross-profile gates.

### rc4 to rc7 - Desktop Gateway Broadens

This line established Desktop smoke as recurring evidence:

- one gateway facade, eight tools, no old names;
- workspace operations with protected-path and traversal DENY;
- document operations including DOCX create/edit;
- Python and Node sandbox;
- external URL blocked before worker;
- temperament promotion;
- INNER content gates;
- journal provenance with SHA and CRLF/LF normalization;
- session-end journal prompt as advisory only, not a background process.

### rc8 to rc9 - Semantic Gates and Qdrant

The rc8/rc9 line is especially useful for showing why test-data quality matters:

- abstract placeholder text was rejected;
- with valid observation-based inputs, the same gates passed;
- retired entries remain physically present but are excluded from the compiled layer;
- Qdrant is treated as a reconstructable index, not canonical memory;
- `require_fresh=true` refuses stale hits;
- `include_retired=true` makes retired sections visible and marked;
- `drop_index` removes only the derived index, not canonical sources.

### rc12 to rc14 - Performance and Semantic Integration

This line shows practical maturation:

- compile modes `boot`, `working`, `full` have different sizes and roles;
- large workspace searches are bounded by scope guards;
- binary and too-large files are skipped instead of blocking the client;
- `scan_tagebuch` remains read-only and transport-stable;
- Qdrant timeouts are structured instead of transport-breaking;
- `working` compile can use fresh semantic hits and fall back when the index is missing or stale.

## Boundary and Governance Scenarios

### Public Tool Boundary

Repeatedly confirmed expectations:

- exactly one public gateway server;
- exactly eight public facade tools;
- no public `plwc_doctor`;
- no raw PBA tools;
- no raw Commander tools;
- no ungoverned filesystem server;
- no second PLwC MCP instance.

### Workspace Access

Confirmed expectations:

- allowed workspace operations can execute with ALLOW;
- missing required parameters produce `validation_error` and are not misclassified as policy DENY;
- parameter errors do not call the adapter;
- parent traversal is blocked;
- protected profile and governance paths cannot be written through normal workspace operations;
- write attempts outside allowed roots are blocked with DENY.

The 2026-07-17 test with a desktop path outside the allowed workspace confirms this point with the new browser/ChatGPT engine as well.

### Profile and Memory Governance

Confirmed expectations:

- profile and memory changes go through plan/apply;
- critical applies require explicit confirmation;
- unsuitable candidates can be rejected for insufficient evidence or wrong semantics;
- duplicate candidates are not silently duplicated;
- governed applies write to canonical profile/journal files in a traceable way;
- normal workspace tools cannot directly overwrite these protected files.

### Journal Guard

Confirmed expectations:

- canonical daily files are preferred;
- suffix files for new daily notes are not silently accepted;
- the guard can enforce a canonical target structure;
- the journal is not an unchecked memory channel.

This matters because [TAGEBUCH_EN.md](TAGEBUCH_EN.md) describes the development path, while memory and temperament only become durable through governance.

### Persona-Layer Control

Confirmed expectations:

- persona layer can be disabled through configuration;
- disabled persona layer leaves hard gates and governance active;
- compile output can omit PERSONA content without losing profile protection;
- persona context remains explicit and inspectable.

This supports the interpretation in [TAGEBUCH_EN.md](TAGEBUCH_EN.md): PLwC does not need hidden persona injection. It can make the portable working context technically controllable.

### CLU Doctor

Confirmed expectations:

- Doctor remains read-only;
- Doctor mutates no profiles, memories, governance files, Qdrant indices, workspace files or documents;
- Doctor returns structured `checked`, `findings` and `not_checked` fields;
- Doctor names explicit non-goals instead of implying coverage.

### Qdrant and Semantic Retrieval

Confirmed expectations:

- Qdrant is an optional index, not canonical truth;
- reindex timeouts are reported structurally;
- busy states do not start a second worker;
- other gateway calls remain available;
- boot compile remains independent of the semantic index;
- stale or missing semantic hits lead to fallback/next-action instead of silent misuse.

## rc18.dev9 Core Evidence

### Package

Confirmed points:

- manifest version `0.2.0-rc18.dev9`;
- runtime version `0.2.0rc18.dev9`;
- package size 537,994 bytes;
- package SHA256 `2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345`;
- 66 files in the filtered package;
- exactly eight public tools;
- only public documentation allowlist content in the package;
- no private smoke, release, privacy or build artifacts in the package;
- no local profiles, logs, tests, `.env`, real security configuration or Python cache files;
- package is unsigned.

### Desktop

Confirmed points:

- runtime reports `0.2.0rc18.dev9` after install/restart;
- SHA was independently recomputed in the Docker sandbox and matched;
- exactly eight public tools visible;
- tool discovery can find PLwC tools without exposing legacy tools;
- extension settings show only expected configuration fields;
- first-run status names canonical bootstrap calls;
- profile precedence prevents a freshly created disposable profile from becoming active unexpectedly;
- persona-layer disablement remains effective;
- CLU Doctor remains read-only;
- reflection alias mapping exists;
- cross-profile reflection write is denied as expected.

## What These Smoke Tests Do Not Claim

This evidence does not claim:

- that a human or metaphysical identity moves between models;
- that a model has broad local filesystem access;
- that all possible MCP hosts or model backends are compatible;
- that Qdrant replaces canonical memory;
- that persona content should be hidden or automatically injected;
- that the current state is a final signed public release.

The technical evidence supports a narrower and stronger claim:

> PLwC can provide a local, governed MCP gateway with a limited workspace, protected profile paths, auditable decisions, controlled memory/reflection flows and explicit context layers. This layer can be used by different tool-call-capable model environments without giving up the security boundary.

## Link to the Change History

The smoke results summarized here explain the later development direction in [CHANGE_HISTORY_EN.md](CHANGE_HISTORY_EN.md): many changes came not from feature wishlists, but from concrete smoke findings, DENY checks, timeout problems, profile-precedence cases and payload-privacy requirements.
