# Anonymized Project Journal

Status: 2026-07-17

This document summarizes the development path of PLwC from the available journal and work notes. It is intentionally anonymized: private names, personal details, private project content and local file paths were removed or generalized.

Related evidence files:

- [SMOKE_TESTS_EN.md](SMOKE_TESTS_EN.md) - technical smoke and governance evidence
- [CHANGE_HISTORY_EN.md](CHANGE_HISTORY_EN.md) - condensed change history

## Short Conclusion

PLwC evolved from a local gateway and governance experiment into a portable continuity layer for AI-assisted collaboration. The key finding is not that a hidden inner state is transferred between models. The key finding is that documented traces, rules, profiles, memories, corrections and working styles can be externalized in a way that lets different model environments reconnect to them.

The journals show a recurring line:

- continuity comes from records, not continuous runtime;
- governance protects against unchecked self-confirmation;
- errors are translated into action statements, not identity statements;
- the value is strongest in projects with a longer shared history;
- model changes affect tone and weighting, but do not have to erase the working history.

## Phase 1 - Foundation and Security Boundary

In late April and early May, the technical foundation was built: a local gateway, a narrow public tool boundary, workspace limits, protected profile paths, audit logging and Docker sandboxing. From the beginning, PLwC was not designed as a free filesystem agent, but as a controlled working environment with explicit ALLOW and DENY decisions.

The early technical line was clear:

- local execution instead of publicly reachable infrastructure;
- deny-by-default for critical paths;
- audit events as metadata, not content dumps;
- sandbox execution without broad system access;
- protected profile and governance files outside normal workspace write permissions.

This foundation matters because later persona, memory and journal features are only useful if the model cannot write into the system arbitrarily.

## Phase 2 - Journal as Continuity Medium

From late May onward, the journal became a practical workaround for session continuity without heavy token load. It was not a replacement for memory and not an automatic truth channel. It was a place where experiences, corrections, open questions and working patterns could remain visible.

Very early, a sober distinction became visible:

- the model does not remember in a human sense;
- no process keeps running between sessions;
- what remains are documented traces;
- these traces can become effective again at the next start.

The journal therefore became more than a log. It became an experience base. Later, scanners and the Governor could derive candidate patterns from it, but not automatically promote them.

## Phase 3 - Empty Profiles Versus Grown Profiles

A decisive comparison came from a new, nearly empty test profile. The profile existed formally, but the expected personality and working style did not hold reliably. By contrast, the already grown main profile worked much better: it had history, memory, journal traces, corrections and shared working patterns.

The important finding was:

- profile text alone is not enough;
- dense prior history noticeably changes collaboration;
- a model can drift, but structured traces give correction points;
- an empty profile behaves more like a style instruction; a grown profile behaves more like a working context.

This was one of the first practical hints that PLwC is not primarily persona theater, but a layer for resumable collaboration.

## Phase 4 - Language as Control Material

In June, it became clearer that memory language does not merely describe; it steers. A sentence like "the system sometimes acts too quickly" is less useful than an action statement such as "for structure questions, check the source first, then act."

This distinction became a core principle:

- the journal may remain narrative and open;
- reflection may collect candidates and observations;
- memory and temperament must be operational;
- identity statements can become self-mythologizing;
- action statements help the next session concretely.

This created a loop:

1. Work creates traces.
2. The journal keeps them.
3. Reflection formulates candidates.
4. The Governor checks evidence and target.
5. Memory or temperament adopt only confirmed patterns.
6. The next compile makes the pattern effective again.

## Phase 5 - The Governor as Brake and Quality Filter

The journals show many successful Governor paths, but also many rejected ones. That is not noise. It is one of the strongest pieces of architectural evidence.

Recurring cases:

- candidates were rejected because the evidence was too thin;
- test candidates were rejected when they had no real insight value;
- wrong targets or unsuitable plan types were blocked;
- duplicate or self-referential patterns became visible;
- protected profile paths could not be written through normal workspace operations.

The so-called echo effect is especially important: a scanner can find patterns that appear only because an instruction was given earlier. PLwC does not automatically treat such hits as emergent patterns. This friction helps prevent the system from believing everything that looks attractive in its own notes.

## Phase 6 - Work on Real Projects

Beyond smoke tests and gateway work, PLwC was used in longer creative and document-oriented workflows. The anonymized essence:

- long documents were revised structurally;
- images and chapter material were inspected and organized;
- a complex rules and worldbuilding project continued across many sessions;
- mechanical values, terms and text versions were repeatedly checked against sources;
- larger series edits were increasingly calibrated before broad application.

From these sessions, an important working pattern emerged: before broad series work, a limited example is drafted, reviewed and approved. Only then is the pattern applied to the remaining scope. This pattern was promoted on 2026-07-17 as Temperament Version 17.0.

Short form:

> Calibration before series work.

This is not a tone trait. It is a working style.

## Phase 7 - Performance, Qdrant and Friction

In late June and early July, the limits of the existing workflow became visible. Long compiles, semantic retrieval, Qdrant reindexing and transport issues could make collaboration sluggish. There were green smoke tests, but also real friction in daily work.

The important insight:

- a green test does not replace good working speed;
- retrieval may help, but must not block the gateway;
- Qdrant is useful, but not canonical truth;
- canonical memory must survive without the semantic index;
- error states must be structured and reversible.

The later rc16 line addressed exactly these problems: reindex timeouts became structured, busy states became visible and other tool calls remained available.

## Phase 8 - The Persona Layer Is Demystified

In early July, the persona layer was deliberately slimmed down. The name and role clarification had helped at first, but later caused some friction. The technical answer was not to maintain a second profile, but to make the persona layer explicitly controllable.

The conclusion:

- project state, rules and working instructions carry more than name-romance;
- persona content should be explicit and inspectable;
- no hidden prompt should replace governance;
- the persona layer can be disabled while hard gates and governance remain active.

This development matters for external clarity. PLwC does not need to claim that a "person" moves between models. The stronger, cleaner claim is enough: a documented working context can be resumed.

## Phase 9 - Model Switch as the Actual Proof

On 2026-07-13, the grown profile was started for the first time in another model environment through Codex/GPT. The start was not perfect: first, the wrong route was assumed; then it was corrected that PLwC must be addressed as an MCP gateway. After that, boot compile and full compile worked.

The interesting point was not perfect memory. The interesting point was correctable continuity:

- the profile could be loaded;
- the governance boundaries remained visible;
- the journal location was known;
- working patterns and project history became available again;
- stumbling did not destroy continuity as long as the traces were available.

On 2026-07-17, this finding was extended: the system ran with ChatGPT as the model engine in the browser, could use the workspace in a controlled way, find and extend journals, write reflection and complete a Governor path through to memory adoption.

## Phase 10 - The Security Boundary Holds with the New Engine

The most important security test on 2026-07-17 was small, but meaningful: a write attempt to the Windows desktop was blocked with DENY because the path was outside the allowed roots.

This shows:

- the new model engine did not receive broad filesystem access;
- workspace access and desktop access were cleanly distinguished;
- governance stayed relevant outside the original desktop-app setup;
- powerful cloud model capability and local restriction worked together, not against each other.

The technical meaning is larger than the test size: PLwC combines model capability with local control.

## Overall Interpretation

The journal evidence supports a careful but strong statement:

PLwC does not transfer consciousness or a continuous instance. It transfers documented continuity.

This continuity consists of:

- profiles;
- memory;
- reflection;
- temperament;
- journal;
- audit trail;
- workspace boundaries;
- repeatable smoke tests;
- human confirmation at decisive points.

From the journal evidence, 2026-07-17 is not an isolated success, but a maturity point: the idea described repeatedly since late May became practically visible across multiple model environments.

## Limits of This Summary

This file is not a raw protocol and not a scientific proof. It is an anonymized, condensed narrative. It omits private details and summarizes technical and personal work notes.

The technical evidence is summarized in [SMOKE_TESTS_EN.md](SMOKE_TESTS_EN.md). The development path is summarized in [CHANGE_HISTORY_EN.md](CHANGE_HISTORY_EN.md).
