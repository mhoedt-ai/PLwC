# Chat Bridge P1-01 Acceptance Evidence

Date: 2026-07-30

Scope: BRIDGE-P1-01 only. Describe guidance and error presentation
(BRIDGE-P1-02), shared build identity (BRIDGE-P1-03), Windows Setup, version
alignment, and the final release test remain outside this acceptance pass.

## Outcome

BRIDGE-P1-01 implementation acceptance passes for the generated Chat Bridge
Primer.

The Primer now contains English and German workspace-handling sections rendered
from one shared seven-rule definition. Stable rule IDs guarantee that both
sections contain the same semantic contract while retaining natural wording in
each language.

The contract directs required intermediate artifacts to a task-specific
`Temp/<task-name>/` directory and final results to the target requested by the
user. It prohibits automatic Temp cleanup, workspace deletion, automatic moves
to `Trashcan/`, and creating or using `Inbox/`. An explicit deletion request
may only lead to an offer to use the existing confirmed workspace `move`
operation with `Trashcan/` as the destination.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Required intermediate products use `Temp/<task-name>/` | PASS | The shared `intermediate_products` rule says that required intermediate products are stored only below the task-specific Temp directory in both languages. |
| Final results use the user-requested target | PASS | The shared `final_results` rule and the guided document example distinguish the final target from intermediate paths. |
| Temp is never cleaned automatically | PASS | The shared `no_temp_cleanup` rule prohibits automatic cleanup and automatic deletion of Temp contents in English and German. |
| Workspace content is not deleted | PASS | The shared `no_workspace_delete` rule explicitly prohibits deleting workspace files or directories. |
| Explicit deletion requests offer a move to `Trashcan/` | PASS | The shared `explicit_delete_offer` rule names `plwc_workspace_operation operation=move` and requires an offer rather than an implicit mutation. Existing Bridge policy continues to require confirmation for workspace moves. |
| Nothing moves to `Trashcan/` automatically | PASS | The shared `no_automatic_trashcan` rule states this prohibition in both languages. |
| `Inbox/` is not created or used | PASS | The shared `no_inbox` rule prohibits both creation and use in both languages. |
| English and German carry the same rule set | PASS | A Primer test extracts stable rule IDs from both rendered sections and compares them with the complete shared rule definition. It also verifies every English and German sentence. |
| Primer tests preserve required terms and prohibitions | PASS | The main Primer regression checks Temp, user targets, cleanup, deletion, Trashcan movement, and Inbox wording alongside all earlier Primer requirements. |
| Guided document workflow keeps intermediates under Temp | PASS | The guided workflow fixture uses two representative document intermediates. The test requires every intermediate path to begin with `Temp/document-acceptance/`, rejects Inbox and Trashcan intermediate paths, and verifies the final PDF remains at the stated user target. |

## Verification Commands

Executed in
`<REPOSITORY_ROOT>\integrations\plwc-chat-bridge\extension`:

```powershell
npm run typecheck
npm test
npm run build:fixture
```

Result: type checking passed, all 114 extension tests passed, and the browser
fixture build passed.

Executed in `<REPOSITORY_ROOT>\integrations\plwc-chat-bridge`:

```powershell
npm run check
```

Result: loopback Bridge build and all 20 loopback tests passed; extension
production build and all 114 extension tests passed.

Executed from the repository root:

```powershell
git diff --check -- <BRIDGE-P1-01 files>
```

Result: passed with Git LF/CRLF conversion warnings only.

## Implementation Boundary

- `extension/src/primer/build-primer.ts` owns the shared bilingual rule
  definition, renders both Primer sections, and supplies the guided document
  workflow example.
- `extension/src/primer/build-primer.test.ts` verifies language parity,
  mandatory terms and prohibitions, and document path placement.
- `extension/README.md` documents the generated Primer workspace contract in
  English.

## Non-P1-01 Items

- No version bump to 1.0.0 was performed.
- No Windows Setup changes were made.
- No PLwC Gateway contract changes were made.
- No BRIDGE-P1-02 error-category or Describe-guidance changes were made.
