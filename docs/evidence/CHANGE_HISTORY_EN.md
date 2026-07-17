# Change-History Evidence

Status: 2026-07-17

This document summarizes the development path of PLwC in anonymized, evidence-oriented form. It contains no links to source files or local raw reports. For context, see:

- [TAGEBUCH_EN.md](TAGEBUCH_EN.md) - anonymized development narrative
- [SMOKE_TESTS_EN.md](SMOKE_TESTS_EN.md) - technical smoke and governance evidence

## Short Overview

PLwC developed in three larger movements:

1. Security and gateway foundation: local MCP gateway, fixed public boundary, workspace and profile protection.
2. Continuity and governance layer: profiles, memory, reflection, journal, Governor and auditable promotions.
3. Model and host independence: persona-layer control, privacy packaging, browser/ChatGPT adapter and resumption of working context outside the original model environment.

## April to Early May 2026 - Foundation

| Date | Area | Content |
| --- | --- | --- |
| 2026-04-30 | Project structure | Initial PLwC Gateway structure is created. |
| 2026-04-30 | Source intake | Source material and migration path are analyzed. |
| 2026-04-30 | Requirements | Traceability and verification plan are created. |
| 2026-04-30 | Policy core | Core policy and boundary tests are introduced. |
| 2026-04-30 | MVP gateway | MVP gateway foundation is completed. |
| 2026-04-30 | Security review | First security review names release blockers. |
| 2026-05-01 | Root/path hardening | Configuration roots and protected paths are hardened. |
| 2026-05-01 | Audit redaction | Audit logging is hardened against sensitive data. |
| 2026-05-01 | Docker policy | Docker sandboxing is aligned with the security model. |
| 2026-05-01 | Governor/PBA | Governor and PBA integration safeguards are hardened. |
| 2026-05-01 | Preflight | Release preflight gates are documented. |

Guiding theme of this phase: security boundary and verifiable limits first, convenience later.

## May 2026 - First Release Candidates and Real Workflows

| Date | Version/State | Content |
| --- | --- | --- |
| 2026-05-02 | v0.1.0-rc1/rc2 | First v0.1 release candidates after packaging, registry, Docker and symlink validations. |
| 2026-05-07 | v0.1.0-rc3 to rc5 | Stabilization of the early gateway and packaging line. |
| 2026-05-23 | v0.2.0-rc1 | Start of the v0.2 line with stronger profile, persona and governance focus. |
| 2026-05-24 | Journal begins as continuity medium | Journal is used as a lightweight session-continuity anchor. |
| 2026-05-25 | Document workflow | Real document work shows the value and limits of existing document operations. |

In this phase, PLwC proves it is not only smoke-test infrastructure. It is used in longer workflows, with errors and workarounds flowing directly back into backlog and governance.

## June 2026 - Memory, Journal and Governor Become Central

| Date | Version/State | Content |
| --- | --- | --- |
| 2026-06-03 | v0.2.0-rc2 | Write/wrapper issues become visible and are fixed; continuity between diagnosis, fix and retest becomes practical. |
| 2026-06-04 | v0.2.0-rc3 | Stabilization and private-beta readiness. Empty profiles are compared with grown profiles. |
| 2026-06-05 | v0.2.0-rc4 | Document editing and governance DENYs are tested successfully. |
| 2026-06-09 | v0.2.0-rc5 | Node.js sandbox and image-path validation are added. |
| 2026-06-10 | v0.2.0-rc6 | Larger smoke run; renewed verification instead of trusting previous state. |
| 2026-06-10 | v0.2.0-rc7 | Session-end journal prompt and provenance/SHA fixes. |
| 2026-06-13 | v0.2.0-rc8 | Memory governance becomes stronger. Suite: 947 passed / 4 skipped in that line. |
| 2026-06-19 | v0.2.0-rc10 | INNER hardening, Qdrant configuration-window toggle and additional P1-P4 fixes. Suite: 939 passed / 4 skipped in that line. |
| 2026-06-19 | v0.2.0-rc11 | Read-only journal pattern scanner is introduced. Suite: 947 passed / 4 skipped in that line. |
| 2026-06-30 | v0.2.0-rc12 | Performance and retrieval friction become more visible. |

Guiding theme of this phase: the system begins to learn from its own traces, but only through review paths. Scanners provide hints, not truth.

## Late June to Early July 2026 - Friction Becomes Product Work

| Date | Version/State | Content |
| --- | --- | --- |
| 2026-06-30 | Performance/Qdrant friction | Semantic retrieval and long compiles show limits in day-to-day use. |
| 2026-07-01 | v0.2.0-rc13 | Crash guard improves timeout behavior; retrieval is still not a load-bearing work core. |
| 2026-07-01 | Evidence before authority | A profile/name detail is corrected only after evidence, not because of bare assertion. |
| 2026-07-02 | Journal vs. reflection | Journal and reflection are understood as separate paths: raw trace vs. governed candidate. |
| 2026-07-03/04 | Working-style calibration | Series work reveals the pattern: calibrate one example first, then apply broadly. |
| 2026-07-05 | rc16.dev0 | Qdrant Maintenance Guard fixes global stall behavior through structured timeout/busy states. |
| 2026-07-05 | rc17.dev0 | CLU Doctor, workspace diagnostics, journal guard and temperament threshold are tested. |

This phase matters because errors are not only repaired. They are translated into rules, tests and working patterns.

## July 2026 - rc18, Packaging, Persona Layer and Public Boundary

| Date | Version/State | Content |
| --- | --- | --- |
| 2026-07-06 | rc18.dev0 package | Command catalog becomes discovery-only; no tool-expansion effect. |
| 2026-07-07 | rc18.dev0 desktop | CLU Runner is tested in the desktop context; read-only and no-leak behavior confirmed. |
| 2026-07-08 | rc18.dev1-dev6 | Several rapid development states improve desktop and package behavior. |
| 2026-07-09 | rc18.dev7 desktop | First-run bootstrap, active-profile precedence and persona-layer disablement confirmed. |
| 2026-07-10 | rc18.dev9 package | Privacy payload filtering, alias metadata and onboarding baseline are packaged. |
| 2026-07-11 | rc18.dev9 desktop | Install/runtime, SHA check, privacy sanity, first-run, precedence, Doctor and reflection aliases pass. |
| 2026-07-12 | Open-beta publication state | Public snapshot and open-beta material are normalized. |
| 2026-07-13 | Registry/contact documentation | Gateway positioning, registry metadata and project contact are documented. |

The most important technical shift: persona and working context become explicitly controllable. The persona layer can be disabled without losing governance or hard gates.

## 2026-07-13 to 2026-07-17 - Cross-Model Reconnection

| Date | Event | Meaning |
| --- | --- | --- |
| 2026-07-13 | First load of the grown profile in Codex/GPT | Boot and full compile work after an initial correction. The working history does not start from zero. |
| 2026-07-17 | Browser/ChatGPT engine with local gateway | Workspace access, journal work, reflection, Governor and memory adoption work in the new model context. |
| 2026-07-17 | Desktop DENY test | Write attempt outside allowed roots is blocked. Governance holds with the new engine. |
| 2026-07-17 | Temperament Version 17.0 | "Calibration before series work" is adopted after journal analysis, Governor review and confirmation. |

This phase is the strongest development-path evidence for the thesis in [TAGEBUCH_EN.md](TAGEBUCH_EN.md): PLwC does not transport a continuous instance, but a documented continuity layer.

## Condensed Technical Development Line

| Topic | Earlier State | Later State |
| --- | --- | --- |
| Public boundary | Gateway facade emerges | exactly eight public tools, no raw servers |
| File access | Workspace root and protected paths | deny-by-default, parent-traversal block, desktop DENY outside allowed roots |
| Audit | Metadata audit | no-content/no-secret logging, high-risk fail-closed |
| Profiles | Profile texts and memory | Governor plan/apply, profile precedence, persona-layer control |
| Journal | Continuity note | scanner source, but not automatic memory |
| Reflection | Observation store | governed candidate path |
| Qdrant | helpful semantic index | optional, stale-aware, not canonical |
| Doctor | individual diagnostics | read-only CLU Runner with checked/findings/not_checked |
| Packaging | MCPB artifacts | privacy-filtered packages with public allowlist |
| Model environment | primarily one desktop app | reconnectable in Codex/GPT and browser/ChatGPT context |

## Evidence-Oriented Conclusion

The change history points to an architecture that learned from real errors:

- a misclassified parameter error led to cleaner workspace diagnostics;
- Qdrant stalls led to timeout/busy guards;
- scanner echo led to stronger skepticism toward automatically found patterns;
- persona friction led to explicit persona-layer control;
- packaging risks led to privacy payload filtering;
- model switching led to the clearer framing of "documented continuity" instead of an instance claim.

The smoke-test evidence for these points is summarized in [SMOKE_TESTS_EN.md](SMOKE_TESTS_EN.md). The narrative interpretation is in [TAGEBUCH_EN.md](TAGEBUCH_EN.md).
